"""Plot controller: tabs, plots, curves, tips and markers.

It covers HLFR-00012 to HLFR-00025, the vertical markers of
HLFR-00028 to HLFR-00031, the zoom reset (HLFR-00035), the grid
(HLFR-00037), undo (HLFR-00040), redo (HLFR-00048) and the delta
markers of HLFR-00043 and HLFR-00044.

It keeps the Workspace model and tells the view what to show. It talks
to the view only through plain method calls with plain values (ids,
names, numbers, numpy arrays), so it can be tested with a fake view
(COR-00003, COR-00009). The view must offer:

- tabs: ``add_tab_view``, ``remove_tab_view``, ``rename_tab_view``,
  ``clear_tab_views``, ``set_current_tab``, ``current_tab_id``,
  ``set_tab_delete_enabled``;
- plots: ``add_plot_view(tab_id_i, plot_id_i, kind_str)``,
  ``remove_plot_view``, ``draw_plot``, ``set_plot_time_range``,
  ``plot_time_range``, ``set_plot_tool``, ``set_delta_first_point``;
- vertical markers: ``set_markers`` (the shared markers, with their
  color (LLFR-00392), drawn on every plot of every tab);
- text notes and arrows: ``set_text_notes(plot_id_i, data_list)`` and
  ``set_arrows(plot_id_i, arrow_data_list)``, drawn only on their plot;
- areas: ``set_areas`` (the shared areas, with their color
  (LLFR-00351), drawn on every time plot of
  every tab) and ``set_plot_areas(plot_id_i, area_data_list)`` (the
  areas of one plot, after it was drawn);
- boxes: ``show_full_tab_notification``,
  ``show_tab_name_taken_notification``,
  ``show_plot_kind_mismatch_notification``, ``ask_marker_name``,
  ``ask_area_name``, and ``ask_color(current_color_str)``, the shared
  color picker (LLFR-00388), which returns the confirmed "#rrggbb" or
  None when cancelled. Every color handler (flag, area, delta marker,
  arrow, text note border and text) also takes the color the user chose
  in the recent colors of the color submenu (LLFR-00419), or "" for
  "Other color...", which opens the picker; the view keeps the recent
  colors list itself;
- grid: ``set_grid_shown``;
- undo and redo: ``set_undo_enabled``, ``set_redo_enabled``;
- handler setters: ``set_signal_double_click_handler``,
  ``set_selected_signals_plot_handler``, ``set_plot_tool_handler``,
  ``set_tab_handlers``,
  ``set_plot_handlers``, ``set_reset_zoom_handler``,
  ``set_grid_handler``, ``set_undo_handler`` and ``set_redo_handler``.

Undo (HLFR-00040): every undoable action of LLFR-00140 saves a snapshot
of the workspace before it changes the model, but only when it really
changes something. Undo restores the snapshot and rebuilds every tab
and plot view from the model. The tab, plot and marker id counters are
never rolled back, so ids stay unique. View-only state is not part of a
snapshot (LLFR-00140 Note): after an undo, every plot shows the time
range shared by all plots, and the grid and the plot tool stay as they
are.

Redo (HLFR-00048): an undo keeps the state it leaves on a redo stack,
and redo returns to it through the same rebuild as undo (LLFR-00192).
A new undoable action empties the redo stack (LLFR-00193), and opening
a file empties both (LLFR-00142).

Shared time axis (LLFR-00070, LLFR-00180): all time plots in all tabs
show one x-axis range, kept here in ``shared_time_range_tuple``. A
range change in any time plot is applied to every other time plot of
every tab, hidden tabs included, so that switching tabs and the PDF
export (LLFR-00129) show it too. The empty tuple stands for the whole
time range of the file: it is used at start, after a zoom reset
(LLFR-00115), when a file is opened and when the last time plot of the
workspace disappears, so that the next time plot starts at the whole
range (LLFR-00180).

Frequency plots (HLFR-00058): a double-click on an FFT signal creates a
frequency plot (``Plot.kind_str`` is FREQUENCY_PLOT_KIND_STR), which
draws its FFT signals against their frequencies in Hz (LLFR-00256). An
FFT signal dropped on a time plot, or another signal dropped on a
frequency plot, is not drawn and the view shows an information box
(LLFR-00257). Each frequency plot keeps its own x-axis range in
``Plot.frequency_range_tuple`` (() for its whole range, from 0 Hz to the
highest frequency of its curves); it never follows the time plots or the
other frequency plots, and the shared time range ignores the frequency
plots (LLFR-00258, LLFR-00070, LLFR-00180, LLFR-00248). The zoom and pan
limits are those of the plot's curves, so adding an FFT signal with a
higher highest frequency widens the limit; removing it narrows the
limit and the kept range is cut to it. Reset zoom returns every
frequency plot to its whole range. A frequency plot never shows the
vertical markers and never places one (LLFR-00259); it still counts as
a plot for the rule that deletes the markers when no plot is left
(LLFR-00205), so the markers stay while a frequency plot exists and come
back on the next time plot. The frequency ranges are view state, like
the shared time range: zooms are not undoable (LLFR-00140), so an undo
or a redo keeps the range each frequency plot shows.

Vertical markers (LLFR-00205): the markers belong to the workspace, not
to a plot, so every plot of every tab shows the same ones, plots created
later included. A placement, move, rename or deletion made on any plot
is one undoable action and is shown on every plot through
``set_markers``, which only redraws the markers. When the last plot of
the workspace goes away, the model deletes the markers in that same
action, so that its undo brings them back.

Areas (HLFR-00066 to HLFR-00069): like the vertical markers, the areas
belong to the workspace and every time plot of every tab shows the same
ones, plots created later included; frequency plots show none
(LLFR-00311). The view reports a created area, or a moved or resized
one, once, when the mouse button is released, with both of its times;
the controller limits them to the time range of the file (LLFR-00119)
and the model refuses an area that would overlap another one
(LLFR-00304). Each creation, move or resize, rename and deletion is one
undoable action (LLFR-00140), shown on every plot through ``set_areas``.
The areas go away with the last plot, in that same action, like the
vertical markers (LLFR-00310).

Delta markers (LLFR-00163 to LLFR-00167): with the Delta X or Delta Y
tool active, the view reports every left click on a curve with the
nearest sample. The first click keeps that point as pending, in
``pending_delta_tuple``, and the view marks it with a dot; a second
click in the same plot places the marker, as one undoable action. A
click in another plot starts again there. The pending point is
discarded, and its dot removed, when the tool changes, when its plot
or its curve goes away, when a file is opened and on every undo. It is
not part of the undo snapshots: only placed markers are.

Arrows (HLFR-00081 to HLFR-00084): like the text notes, the arrows
belong to the plot they were drawn on (``Plot.arrow_list``) and go away
with it (LLFR-00375). The view reports a drawn arrow, or a moved,
rotated or stretched one, once, when the mouse button is released, with
the x and y values of both ends; the arrowhead is always at the second
end. Each drawing, change of the ends, change of color and deletion is
one undoable action (LLFR-00140). Arrows are never saved in a layout
file (LLFR-00226).

Layout files (HLFR-00049, HLFR-00050): ``layout_dict`` returns the
content of a layout file for the current layout, and ``load_layout``
rebuilds the layout of a file in the workspace (model.layout_file),
applies its time range and grid, clears the undo and redo history
(LLFR-00238) and shows every tab and plot again. The layout controller
runs the dialogs and the boxes.

Every handler validates the ids it gets from the view and ignores
unknown ones, so a stale request never raises (PCR-00025).
"""

import math

import numpy as np

from controller.plot_tools import (
    AREA_TOOL_STR, DELTA_X_TOOL_STR, MARKER_TOOL_STR, NO_TOOL_STR,
    is_delta_tool, is_known_plot_tool)
from model.layout_file import build_layout_dict, rebuild_layout
from model.undo_history import UndoHistory
from model.workspace import (
    DELTA_X_KIND_STR, DELTA_Y_KIND_STR, FREQUENCY_PLOT_KIND_STR,
    TIME_PLOT_KIND_STR, WHOLE_FREQUENCY_RANGE_TUPLE, Workspace)


class PlotController:
    """Runs the plotting actions of the user on the model and the view.

    Inputs:
        view: the view facade (MainWindow, or a fake view in tests).
        file_controller: the FileController; this controller listens to
            it for opened files.
        workspace: optional Workspace; a new one is made when None.
    Attributes:
        view: the view facade.
        workspace: the Workspace with the tabs, plots and curves.
        signal_file: the open SignalFile, or None before the first file.
        plot_tool_str: the active plot tool (a name of
            controller.plot_tools), NO_TOOL_STR when none is active.
        grid_shown_b: True while the grid is shown on the plots.
        shared_time_range_tuple: the (start_s, end_s) range shown by
            every time plot, or () for the whole time range of the file.
        undo_history: the UndoHistory of the saved workspace states.
        pending_delta_tuple: the first point of a delta marker being
            placed, as (plot_id_i, (signal_name_str, time_s, value_f)),
            or () when no first point is picked (LLFR-00163).
    """

    def __init__(self, view, file_controller, workspace=None) -> None:
        """Store the parts, connect the handlers and show the first tab.

        Inputs:
            view: the view facade.
            file_controller: the FileController that opens files.
            workspace: optional Workspace.
        Outputs: none.
        """
        # LLFR-00024: the workspace starts with one tab.
        if workspace is None:
            workspace = Workspace()
        self.view = view
        self.workspace = workspace
        self.signal_file = None
        self.plot_tool_str = NO_TOOL_STR
        # LLFR-00147: the grid is shown at every start; no choice of an
        # earlier run is kept.
        self.grid_shown_b = True
        # LLFR-00070, LLFR-00180: no plot yet, so the whole range.
        self.shared_time_range_tuple = ()
        # LLFR-00139: the 30 most recent undoable actions;
        # LLFR-00192: and the undone ones, for redo.
        self.undo_history = UndoHistory()
        # LLFR-00163: no delta marker point is picked yet.
        self.pending_delta_tuple = ()
        # LLFR-00242: the synthetic signals that can be plotted like the
        # data file signals; set by the SyntheticController.
        self.synthetic_store = None
        # LLFR-00015, LLFR-00016: reset the tabs for every opened file.
        file_controller.add_file_opened_listener(self.on_file_opened)
        # LLFR-00019: signal list requests.
        view.set_signal_double_click_handler(self.on_signal_double_clicked)
        # LLFR-00295: the Enter key plots the selected signals.
        view.set_selected_signals_plot_handler(
            self.on_selected_signals_plotted)
        # LLFR-00079, LLFR-00109: the plot tool buttons of the top panel.
        view.set_plot_tool_handler(self.on_plot_tool_changed)
        # LLFR-00026, LLFR-00028, LLFR-00030: tab menu and "+" button.
        view.set_tab_handlers(self.on_add_tab, self.on_delete_tab,
                              self.on_rename_tab)
        # LLFR-00021, LLFR-00039, LLFR-00041, LLFR-00045, LLFR-00047,
        # LLFR-00049, LLFR-00070: requests made on a plot.
        # LLFR-00081, LLFR-00086, LLFR-00088, LLFR-00091: requests made
        # on the vertical markers of a plot.
        view.set_plot_handlers(
            curve_delete_handler=self.on_curve_delete,
            curve_width_handler=self.on_curve_width,
            plot_delete_handler=self.on_plot_delete,
            # LLFR-00297: a drop of one or several selected signals; the
            # plot widgets send every drop here.
            signals_drop_handler=self.on_signals_dropped,
            # LLFR-00021: the one-name entry, kept for callers that drop
            # a single name (the fake views of the tests); no plot
            # widget signal uses it.
            signal_drop_handler=self.on_signal_dropped,
            tip_pin_handler=self.on_tip_pin,
            pinned_tip_delete_handler=self.on_pinned_tip_delete,
            pinned_tip_move_handler=self.on_pinned_tip_move,
            time_range_handler=self.on_time_range_changed,
            marker_place_handler=self.on_marker_place,
            marker_move_handler=self.on_marker_move,
            marker_rename_handler=self.on_marker_rename,
            marker_delete_handler=self.on_marker_delete,
            # LLFR-00163, LLFR-00164, LLFR-00176: the delta markers.
            delta_point_pick_handler=self.on_delta_point_pick,
            delta_marker_delete_handler=self.on_delta_marker_delete,
            # LLFR-00409: "Color" in the delta marker menu.
            delta_marker_color_handler=self.on_delta_marker_color,
            # LLFR-00334, LLFR-00339, LLFR-00342, LLFR-00343: the text
            # notes of a plot.
            text_note_create_handler=self.on_text_note_create,
            text_note_move_handler=self.on_text_note_move,
            text_note_edit_handler=self.on_text_note_edit,
            text_note_delete_handler=self.on_text_note_delete,
            # LLFR-00385, LLFR-00387: the size and the colors of a note.
            text_note_size_handler=self.on_text_note_size,
            text_note_border_color_handler=self.on_text_note_border_color,
            text_note_text_color_handler=self.on_text_note_text_color,
            # LLFR-00392: "Color" in the flag menu.
            marker_color_handler=self.on_marker_color)
        # LLFR-00372, LLFR-00376, LLFR-00377, LLFR-00379, LLFR-00380: the
        # requests made on the arrows of a plot.
        view.set_plot_handlers(
            arrow_create_handler=self.on_arrow_create,
            arrow_change_handler=self.on_arrow_change,
            arrow_color_handler=self.on_arrow_color,
            arrow_delete_handler=self.on_arrow_delete)
        # LLFR-00304, LLFR-00312, LLFR-00313, LLFR-00315, LLFR-00316: the
        # requests made on the areas of a plot.
        view.set_plot_handlers(
            area_create_handler=self.on_area_create,
            area_change_handler=self.on_area_change,
            area_rename_handler=self.on_area_rename,
            area_color_handler=self.on_area_color,
            area_delete_handler=self.on_area_delete)
        # LLFR-00412 to LLFR-00417: the "Delete all ..." options of the
        # pinned tip, delta marker, flag and area menus.
        view.set_plot_handlers(
            plot_pinned_tips_delete_handler=self.on_plot_pinned_tips_delete,
            all_pinned_tips_delete_handler=self.on_all_pinned_tips_delete,
            plot_delta_markers_delete_handler=(
                self.on_plot_delta_markers_delete),
            all_delta_markers_delete_handler=(
                self.on_all_delta_markers_delete),
            all_markers_delete_handler=self.on_all_markers_delete,
            all_areas_delete_handler=self.on_all_areas_delete)
        # LLFR-00115: the Reset zoom button of the top panel.
        view.set_reset_zoom_handler(self.on_reset_zoom)
        # LLFR-00122, LLFR-00123: the Grid button of the top panel.
        view.set_grid_handler(self.on_grid_toggled)
        view.set_grid_shown(self.grid_shown_b)
        # LLFR-00136, LLFR-00137: the Undo button and its shortcut.
        view.set_undo_handler(self.on_undo)
        # LLFR-00190, LLFR-00191: the Redo button and its shortcut.
        view.set_redo_handler(self.on_redo)
        # LLFR-00024: show the tabs of the model (one empty tab).
        self.rebuild_tab_views()
        # LLFR-00141, LLFR-00194: nothing to undo or redo at start.
        self.update_undo_enabled()

    # ----------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------

    def rebuild_tab_views(self) -> None:
        """Replace all tab views with the tabs of the workspace.

        Inputs: none.
        Outputs: none. The first tab becomes the current tab.
        """
        # LLFR-00015: close every tab and plot shown.
        self.view.clear_tab_views()
        # LLFR-00016, LLFR-00024: show the model's tabs (one empty tab).
        for tab in self.workspace.tab_list:
            self.view.add_tab_view(tab.tab_id_i, tab.name_str)
        self.view.set_current_tab(self.workspace.tab_list[0].tab_id_i)
        self.update_tab_delete_enabled()

    def update_tab_delete_enabled(self) -> None:
        """Enable the tab menu's "Delete" only when a tab may be deleted.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00066: the last tab cannot be deleted.
        self.view.set_tab_delete_enabled(self.workspace.can_delete_tab())

    def update_undo_enabled(self) -> None:
        """Enable the Undo and Redo buttons only while they can act.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00141: disabled, and paler, when nothing is left to undo.
        self.view.set_undo_enabled(self.undo_history.can_undo())
        # LLFR-00194: disabled, and paler, when nothing is left to redo.
        self.view.set_redo_enabled(self.undo_history.can_redo())

    def take_snapshot(self):
        """Save the workspace state from before an action.

        Inputs: none.
        Outputs: a WorkspaceSnapshot, with the selected tab.
        """
        # LLFR-00140: taken before an undoable action changes the model.
        return self.workspace.snapshot(self.view.current_tab_id())

    def record_undo(self, snapshot) -> None:
        """Keep a snapshot for undo when the action changed the model.

        Inputs:
            snapshot: the WorkspaceSnapshot taken before the action.
        Outputs: none. Nothing is recorded when the workspace is the
            same as in the snapshot.
        """
        # LLFR-00140: only an action that changed something is undoable.
        if self.workspace.is_unchanged_since(snapshot):
            return
        # LLFR-00139: the history keeps the 30 most recent actions;
        # LLFR-00193: and forgets the undone ones.
        self.undo_history.record(snapshot)
        self.update_undo_enabled()

    def set_synthetic_store(self, synthetic_store) -> None:
        """Use a store of synthetic signals for the curves.

        Inputs:
            synthetic_store: the SyntheticSignalStore of the open data
                file, or None for no synthetic signals.
        Outputs: none.
        """
        # LLFR-00242: synthetic signals are plotted like data signals.
        self.synthetic_store = synthetic_store

    def is_synthetic_signal(self, signal_name_str: str) -> bool:
        """Tell whether a name is the name of a synthetic signal.

        Inputs:
            signal_name_str: a signal name.
        Outputs: True when the synthetic store holds the signal.
        """
        # LLFR-00242: synthetic signals are in the signal list too.
        return (self.synthetic_store is not None
                and self.synthetic_store.contains(signal_name_str))

    def is_fft_signal(self, signal_name_str: str) -> bool:
        """Tell whether a signal is an FFT signal.

        Inputs:
            signal_name_str: a signal name.
        Outputs: True for an FFT signal, which is drawn only in frequency
            plots (HLFR-00058, LLFR-00257).
        """
        # LLFR-00256, LLFR-00257: FFT signals have frequency on x.
        return (self.synthetic_store is not None
                and self.synthetic_store.is_fft(signal_name_str))

    def plot_kind_for_signal(self, signal_name_str: str) -> str:
        """Return the kind of plot a signal is drawn in.

        Inputs:
            signal_name_str: a signal name.
        Outputs: FREQUENCY_PLOT_KIND_STR for an FFT signal, else
            TIME_PLOT_KIND_STR.
        """
        # LLFR-00256: an FFT signal gets a frequency plot; LLFR-00068:
        # every other signal a time plot.
        if self.is_fft_signal(signal_name_str):
            return FREQUENCY_PLOT_KIND_STR
        return TIME_PLOT_KIND_STR

    def has_signal(self, signal_name_str: str) -> bool:
        """Tell whether a signal of the signal list can be plotted.

        Inputs:
            signal_name_str: the signal name sent by the view.
        Outputs: True when a file is open and the name is one of its
            signals or a synthetic signal (FFT signals included).
        """
        # LLFR-00020, LLFR-00021, LLFR-00055: the signals of the open
        # file, Time included, can be drawn.
        if self.signal_file is None:
            return False
        if signal_name_str in self.signal_file.signal_dict:
            return True
        # LLFR-00242: and the synthetic signals; LLFR-00256: FFT signals
        # too, in frequency plots.
        return self.is_synthetic_signal(signal_name_str)

    def signal_values(self, signal_name_str: str):
        """Return the samples of a data file or synthetic signal.

        Inputs:
            signal_name_str: name of a signal of the signal list.
        Outputs: its numpy array, one value per time sample.
        Raises: KeyError for an unknown name.
        """
        # LLFR-00242: synthetic signals are looked up by current name.
        if signal_name_str in self.signal_file.signal_dict:
            return self.signal_file.signal_array(signal_name_str)
        if self.is_synthetic_signal(signal_name_str):
            return self.synthetic_store.get(signal_name_str).value_array
        raise KeyError(signal_name_str)

    def signal_x_values(self, signal_name_str: str):
        """Return the x-axis values a signal is drawn against.

        Inputs:
            signal_name_str: name of a signal of the signal list.
        Outputs: the numpy array of the frequencies in Hz of an FFT
            signal, or else the time signal of the file, in seconds.
        """
        # LLFR-00256: an FFT signal is drawn against its frequencies.
        if self.is_fft_signal(signal_name_str):
            return self.synthetic_store.get(signal_name_str).frequency_array
        # LLFR-00068: every other signal against the time signal.
        return self.signal_file.time_array

    def curve_data_list(self, plot) -> list:
        """Return the drawing data of every curve of a plot.

        Inputs:
            plot: the model Plot.
        Outputs: a list of tuples (signal_name_str, x_array,
            value_array, color_str, width_i) in curve order; x_array is
            the time signal in a time plot and the frequencies in Hz in
            a frequency plot.
        """
        # LLFR-00068: every curve of a time plot is drawn against the
        # time signal; LLFR-00256: of a frequency plot, against its
        # frequencies. LLFR-00033, LLFR-00034, LLFR-00041, LLFR-00052:
        # colors and widths come from the model. LLFR-00242: synthetic
        # signals too.
        return [(curve.signal_name_str,
                 self.signal_x_values(curve.signal_name_str),
                 self.signal_values(curve.signal_name_str),
                 curve.color_str, curve.width_i)
                for curve in plot.curve_list]

    def frequency_limit_tuple(self, plot) -> tuple:
        """Return the whole frequency range of a frequency plot.

        Inputs:
            plot: the model Plot, a frequency plot.
        Outputs: (0.0, highest frequency of its curves in Hz), or ()
            when it has no curve with a finite frequency above 0 Hz.
        """
        # LLFR-00258: from 0 Hz up to the highest frequency of its
        # curves; it grows when a curve with higher frequencies is added.
        highest_hz = -math.inf
        for curve in plot.curve_list:
            frequency_array = np.asarray(
                self.signal_x_values(curve.signal_name_str), dtype=float)
            frequency_array = frequency_array[np.isfinite(frequency_array)]
            if frequency_array.size:
                highest_hz = max(highest_hz, float(np.max(frequency_array)))
        if not highest_hz > 0.0:
            return ()
        return (0.0, highest_hz)

    def pinned_tip_data_list(self, plot) -> list:
        """Return the drawing data of every pinned tip of a plot.

        Inputs:
            plot: the model Plot.
        Outputs: a list of tuples (signal_name_str, time_s, value_f,
            label_offset_tuple) in the order the tips were pinned.
        """
        # LLFR-00045: the pinned tips; LLFR-00152: each tip with the
        # offset of its label.
        return [(pinned_tip.signal_name_str, pinned_tip.time_s,
                 pinned_tip.value_f, pinned_tip.label_offset_tuple)
                for pinned_tip in plot.pinned_tip_list]

    def plot_marker_data_list(self, plot) -> list:
        """Return the vertical markers a plot shows.

        Inputs:
            plot: the model Plot.
        Outputs: marker_data_list() for a time plot, [] for a frequency
            plot.
        """
        # LLFR-00205: every time plot shows every marker; LLFR-00259: a
        # frequency plot shows none.
        if plot.is_frequency_plot():
            return []
        return self.marker_data_list()

    def marker_data_list(self) -> list:
        """Return the drawing data of every vertical marker.

        Inputs: none.
        Outputs: a list of tuples (marker_id_i, name_str, time_s,
            color_str) in the order the markers were placed; the same for
            every plot.
        """
        # LLFR-00084, LLFR-00092: the label shows the name and the time.
        # LLFR-00205: the markers are shared by every plot.
        # LLFR-00392: each drawn in its own color.
        return [(marker.marker_id_i, marker.name_str, marker.time_s,
                 marker.color_str)
                for marker in self.workspace.marker_list]

    def show_markers(self) -> None:
        """Draw the shared vertical markers again on every plot.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00081, LLFR-00086, LLFR-00091, LLFR-00112, LLFR-00205: a
        # change made on one plot is shown on every plot of every tab;
        # only the markers are redrawn, not the curves.
        self.view.set_markers(self.marker_data_list())

    def area_data_list(self) -> list:
        """Return the drawing data of every area.

        Inputs: none.
        Outputs: a list of tuples (area_id_i, name_str, start_s, end_s,
            color_str) in creation order; the same for every time
            plot.
        """
        # LLFR-00307, LLFR-00308: the label shows the name and the times.
        # LLFR-00310: the areas are shared by every time plot.
        return list(self.workspace.area_state_tuple())

    def plot_area_data_list(self, plot) -> list:
        """Return the areas a plot shows.

        Inputs:
            plot: the model Plot.
        Outputs: area_data_list() for a time plot, [] for a frequency
            plot.
        """
        # LLFR-00310: every time plot shows every area; LLFR-00311: a
        # frequency plot shows none.
        if plot.is_frequency_plot():
            return []
        return self.area_data_list()

    def show_areas(self) -> None:
        """Draw the shared areas again on every plot.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00304, LLFR-00312, LLFR-00315, LLFR-00316, LLFR-00310: a
        # change made on one plot is shown on every time plot of every
        # tab; only the areas are redrawn, not the curves.
        self.view.set_areas(self.area_data_list())

    def delta_marker_data_list(self, plot) -> list:
        """Return the drawing data of every delta marker of a plot.

        Inputs:
            plot: the model Plot.
        Outputs: a list of tuples (delta_marker_id_i, kind_str,
            first_point_tuple, second_point_tuple, delta_f, color_str) in
            the order the markers were placed; each point is
            (signal_name_str, time_s, value_f), delta_f is the second
            point minus the first (LLFR-00169, LLFR-00171) and color_str
            the marker's color (LLFR-00172, LLFR-00409).
        """
        # LLFR-00168, LLFR-00170, LLFR-00174: every delta marker, with
        # the value it shows computed by the model. LLFR-00409: and its
        # color.
        return [(delta_marker.delta_marker_id_i, delta_marker.kind_str,
                 tuple(delta_marker.first_point_tuple),
                 tuple(delta_marker.second_point_tuple),
                 delta_marker.delta_f(), delta_marker.color_str)
                for delta_marker in plot.delta_marker_list]

    def text_note_data_list(self, plot) -> list:
        """Return the drawing data of every text note of a plot.

        Inputs:
            plot: the model Plot.
        Outputs: a list of tuples (text_str, time_s, value_f, size_i,
            border_color_str, text_color_str) in the order the notes were
            written; time_s is in Hz on a frequency plot.
        """
        # LLFR-00336, LLFR-00337, LLFR-00340: the notes of this plot only,
        # each with the text and the place it is attached to.
        # LLFR-00385, LLFR-00387: and its chosen size and colors.
        return [(text_note.text_str, text_note.time_s, text_note.value_f,
                 text_note.size_i, text_note.border_color_str,
                 text_note.text_color_str)
                for text_note in plot.text_note_list]

    def arrow_data_list(self, plot) -> list:
        """Return the drawing data of every arrow of a plot.

        Inputs:
            plot: the model Plot.
        Outputs: a list of tuples (start_time_s, start_value_f,
            end_time_s, end_value_f, color_str) in the order the arrows
            were drawn; the arrowhead is at the end; the x values are in
            Hz on a frequency plot.
        """
        # LLFR-00373, LLFR-00374, LLFR-00375: the arrows of this plot
        # only, each with its two ends and its color.
        return [(arrow.start_time_s, arrow.start_value_f, arrow.end_time_s,
                 arrow.end_value_f, arrow.color_str)
                for arrow in plot.arrow_list]

    def all_plot_list(self) -> list:
        """Return every plot of every tab.

        Inputs: none.
        Outputs: a list of Plot objects, tab by tab, top to bottom.
        """
        # LLFR-00070, LLFR-00258: time plots and frequency plots.
        return [plot for tab in self.workspace.tab_list
                for plot in tab.plot_list]

    def time_plot_list(self) -> list:
        """Return every time plot of every tab.

        Inputs: none.
        Outputs: a list of Plot objects, tab by tab, top to bottom,
            without the frequency plots.
        """
        # LLFR-00070: the plots that share the time range; LLFR-00258:
        # frequency plots never follow it.
        return [plot for plot in self.all_plot_list()
                if not plot.is_frequency_plot()]

    def forget_range_without_plots(self) -> None:
        """Go back to the whole time range when no time plot is left.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00180: with no other time plot, a new time plot shows the
        # whole time range of the file, whatever range was shared
        # before; the frequency plots do not keep the shared range.
        if not self.time_plot_list():
            self.shared_time_range_tuple = ()

    def frequency_range_tuple(self, plot) -> tuple:
        """Return the range a frequency plot shows, within its limits.

        Inputs:
            plot: the model Plot, a frequency plot.
        Outputs: (start_hz, end_hz): its kept range cut to its whole
            frequency range; () for its whole range, also when the kept
            range is outside the whole range.
        """
        # LLFR-00258: zooms and pans stay within 0 Hz and the highest
        # frequency of the plot's curves, which can drop when a curve is
        # removed.
        limit_tuple = self.frequency_limit_tuple(plot)
        if not plot.frequency_range_tuple or not limit_tuple:
            return WHOLE_FREQUENCY_RANGE_TUPLE
        start_hz = min(max(plot.frequency_range_tuple[0], limit_tuple[0]),
                       limit_tuple[1])
        end_hz = min(max(plot.frequency_range_tuple[1], limit_tuple[0]),
                     limit_tuple[1])
        if not end_hz > start_hz:
            return WHOLE_FREQUENCY_RANGE_TUPLE
        return (start_hz, end_hz)

    def apply_shared_range(self, plot) -> None:
        """Show its x-axis range in a plot that was just drawn.

        Inputs:
            plot: the model Plot.
        Outputs: none. A time plot shows the shared time range, a
            frequency plot its own range; with no such range the plot
            keeps the whole range that draw_plot gave it.
        """
        # LLFR-00258: a frequency plot keeps its own range, cut to its
        # limits; the view's set_plot_time_range does not report back.
        if plot.is_frequency_plot():
            plot.frequency_range_tuple = self.frequency_range_tuple(plot)
            if plot.frequency_range_tuple:
                start_hz, end_hz = plot.frequency_range_tuple
                self.view.set_plot_time_range(plot.plot_id_i, start_hz,
                                              end_hz)
            return
        # LLFR-00070, LLFR-00180: the range of all the other time plots.
        if self.shared_time_range_tuple:
            start_s, end_s = self.shared_time_range_tuple
            self.view.set_plot_time_range(plot.plot_id_i, start_s, end_s)

    def redraw_plot(self, plot) -> None:
        """Draw a plot's curves, pinned tips and vertical markers again.

        Inputs:
            plot: the model Plot, new or already shown.
        Outputs: none. The plot shows the shared time range afterwards.
        """
        # LLFR-00068: time on the x-axis; LLFR-00045: pinned tips.
        # LLFR-00205: the shared markers, also on a plot created after
        # them, are drawn on the same path as the curves.
        # LLFR-00168, LLFR-00170: and the delta markers.
        # LLFR-00259: a frequency plot gets no vertical marker.
        self.view.draw_plot(plot.plot_id_i, self.curve_data_list(plot),
                            self.pinned_tip_data_list(plot),
                            self.plot_marker_data_list(plot),
                            self.delta_marker_data_list(plot))
        # LLFR-00310: the shared areas, also on a plot created after
        # them; LLFR-00311: none on a frequency plot.
        self.view.set_plot_areas(plot.plot_id_i,
                                 self.plot_area_data_list(plot))
        # LLFR-00337, LLFR-00340: and the text notes of the plot.
        self.view.set_text_notes(plot.plot_id_i,
                                 self.text_note_data_list(plot))
        # LLFR-00374, LLFR-00375: and the arrows of the plot.
        self.view.set_arrows(plot.plot_id_i, self.arrow_data_list(plot))
        # LLFR-00070, LLFR-00180: draw_plot shows the whole range; a new
        # or redrawn time plot takes the range shared by all time plots.
        # LLFR-00258: a frequency plot its own range.
        self.apply_shared_range(plot)

    # ----------------------------------------------------------------
    # File
    # ----------------------------------------------------------------

    def on_file_opened(self, signal_file, replaced_b: bool) -> None:
        """Close every tab and plot and keep the new file.

        Inputs:
            signal_file: the SignalFile that was opened.
            replaced_b: True when it replaced another file.
        Outputs: none.
        """
        # LLFR-00013: the new file is the one plotted from now on.
        self.signal_file = signal_file
        # LLFR-00167: a first point of the previous file is discarded.
        self.discard_pending_delta()
        # LLFR-00015, LLFR-00016: close all tabs and plots and leave one
        # tab with no plots (also harmless for the first file).
        # LLFR-00205, LLFR-00085: every vertical marker is deleted and
        # the numbering restarts at "Flag 1"; this is not undoable.
        # LLFR-00310, LLFR-00309: so is every area, and the numbering
        # restarts at "Area 1".
        self.workspace.reset()
        # LLFR-00180: the new file's plots start at its whole range.
        self.shared_time_range_tuple = ()
        # LLFR-00142: the actions on the previous file cannot be undone
        # or redone.
        self.undo_history.clear()
        self.update_undo_enabled()
        self.rebuild_tab_views()

    # ----------------------------------------------------------------
    # Signal list
    # ----------------------------------------------------------------

    def on_signal_double_clicked(self, signal_name_str: str) -> None:
        """Create a plot in the current tab that draws the signal.

        Inputs:
            signal_name_str: the double-clicked signal name.
        Outputs: none.
        """
        # LLFR-00019, LLFR-00055: any signal of the open file, Time too.
        if not self.has_signal(signal_name_str):
            return
        tab = self.workspace.find_tab(self.view.current_tab_id())
        if tab is None:
            return
        # LLFR-00140: creating a plot is undoable, a frequency plot too.
        snapshot = self.take_snapshot()
        # LLFR-00031, LLFR-00256: a full tab gets no new plot; an FFT
        # signal gets a frequency plot, which counts towards the maximum.
        plot = self.workspace.add_plot(
            tab.tab_id_i, self.plot_kind_for_signal(signal_name_str))
        if plot is None:
            # LLFR-00032: tell the user to add a tab or delete a plot.
            self.view.show_full_tab_notification()
            return
        # LLFR-00019, LLFR-00069: the new plot goes below the others.
        self.view.add_plot_view(tab.tab_id_i, plot.plot_id_i, plot.kind_str)
        # LLFR-00020, LLFR-00052: draw the signal with width 1.
        plot.add_curve(signal_name_str)
        # LLFR-00140: the plot and its curve are one undoable action.
        self.record_undo(snapshot)
        # LLFR-00180: the new plot shows the range of the other plots.
        self.redraw_plot(plot)

    def plottable_signal_list(self, signal_name_list: list) -> list:
        """Return the names that can be plotted, once each, in order.

        Inputs:
            signal_name_list: signal names sent by the view, in the
                order of the signal list.
        Outputs: the names of signals of the open file or synthetic
            signals, without repeats, in the given order.
        """
        # LLFR-00295, LLFR-00297: the selected signals, in list order.
        plottable_list = []
        for signal_name_str in signal_name_list:
            signal_name_str = str(signal_name_str)
            if (self.has_signal(signal_name_str)
                    and signal_name_str not in plottable_list):
                plottable_list.append(signal_name_str)
        return plottable_list

    def on_selected_signals_plotted(self, signal_name_list: list) -> None:
        """Create one plot in the current tab that draws every signal.

        Inputs:
            signal_name_list: the selected signal names, in the order
                of the signal list (Enter key).
        Outputs: none.
        """
        # LLFR-00296: nothing selected, nothing plotted, no message.
        plottable_list = self.plottable_signal_list(signal_name_list)
        if not plottable_list:
            return
        tab = self.workspace.find_tab(self.view.current_tab_id())
        if tab is None:
            return
        # LLFR-00300: FFT signals and other signals cannot share a plot;
        # nothing is drawn and the box of LLFR-00257 is shown.
        kind_set = {self.plot_kind_for_signal(signal_name_str)
                    for signal_name_str in plottable_list}
        if len(kind_set) != 1:
            self.view.show_plot_kind_mismatch_notification()
            return
        # LLFR-00301: the new plot and all its curves are one undoable
        # action.
        snapshot = self.take_snapshot()
        # LLFR-00295, LLFR-00031: a full tab gets no new plot; when every
        # signal is an FFT signal the plot is a frequency plot
        # (LLFR-00256).
        plot = self.workspace.add_plot(tab.tab_id_i, kind_set.pop())
        if plot is None:
            # LLFR-00032: tell the user to add a tab or delete a plot.
            self.view.show_full_tab_notification()
            return
        # LLFR-00069: the new plot goes below the others.
        self.view.add_plot_view(tab.tab_id_i, plot.plot_id_i, plot.kind_str)
        # LLFR-00295, LLFR-00033, LLFR-00034: every signal in list order,
        # so the curves get the palette colors in that order.
        for signal_name_str in plottable_list:
            plot.add_curve(signal_name_str)
        self.record_undo(snapshot)
        # LLFR-00180: the new plot shows the range of the other plots.
        self.redraw_plot(plot)

    def on_signal_dropped(self, plot_id_i: int,
                          signal_name_str: str) -> None:
        """Draw a dropped signal in the plot it was dropped on.

        Inputs:
            plot_id_i: id of the plot the signal was dropped on.
            signal_name_str: the dropped signal name.
        Outputs: none.
        """
        # LLFR-00021: a drop of one signal is a drop of a list of one.
        self.on_signals_dropped(plot_id_i, [signal_name_str])

    def on_signals_dropped(self, plot_id_i: int,
                           signal_name_list: list) -> None:
        """Draw the dropped signals in the plot they were dropped on.

        Inputs:
            plot_id_i: id of the plot the signals were dropped on.
            signal_name_list: the dropped signal names, in the order of
                the signal list.
        Outputs: none.
        """
        # LLFR-00022, LLFR-00023: only a drop on a known plot does
        # anything; there is no other path from a drop to a new plot.
        plot = self.workspace.find_plot(plot_id_i)
        plottable_list = self.plottable_signal_list(signal_name_list)
        if plot is None or not plottable_list:
            return
        # LLFR-00257, LLFR-00300: an FFT signal on a time plot, or
        # another signal on a frequency plot, is not drawn; when one of
        # the dropped signals cannot be drawn there, none is, and an
        # information box says why.
        for signal_name_str in plottable_list:
            if self.plot_kind_for_signal(signal_name_str) != plot.kind_str:
                self.view.show_plot_kind_mismatch_notification()
                return
        # LLFR-00140, LLFR-00301: the curves of one drop are one
        # undoable action.
        snapshot = self.take_snapshot()
        # LLFR-00056, LLFR-00057, LLFR-00299: a signal already shown is
        # not drawn again, and no message is shown; the others are drawn
        # in list order (LLFR-00297).
        added_count_i = 0
        for signal_name_str in plottable_list:
            if plot.add_curve(signal_name_str) is not None:
                added_count_i += 1
        if added_count_i == 0:
            return
        self.record_undo(snapshot)
        # LLFR-00021, LLFR-00297: draw the signals in that plot.
        self.redraw_plot(plot)

    # ----------------------------------------------------------------
    # Curves and plots
    # ----------------------------------------------------------------

    def on_curve_delete(self, plot_id_i: int, signal_name_str: str) -> None:
        """Remove a curve; delete the plot when it was the last one.

        Inputs:
            plot_id_i: id of the plot.
            signal_name_str: name of the signal to remove.
        Outputs: none.
        """
        # LLFR-00140: removing a curve is undoable, together with the
        # plot it may delete (LLFR-00051).
        snapshot = self.take_snapshot()
        # LLFR-00039: remove the curve from the plot.
        # LLFR-00178: the model also removes the delta markers with a
        # point on that curve, in the same undoable action.
        if not self.workspace.remove_curve(plot_id_i, signal_name_str):
            return
        self.record_undo(snapshot)
        # LLFR-00167: a first point on the removed curve is discarded.
        self.discard_pending_delta_if_gone()
        plot = self.workspace.find_plot(plot_id_i)
        if plot is None:
            # LLFR-00051, LLFR-00049, LLFR-00050: the plot had no curves
            # left and was deleted; the others fill the space.
            self.view.remove_plot_view(plot_id_i)
            # LLFR-00180: it may have been the last plot of all.
            # LLFR-00205: then the model also deleted every vertical
            # marker, in this same undoable action.
            self.forget_range_without_plots()
            return
        self.redraw_plot(plot)

    def on_curve_width(self, plot_id_i: int, signal_name_str: str,
                       width_i: int) -> None:
        """Draw a curve with a preset width.

        Inputs:
            plot_id_i: id of the plot.
            signal_name_str: name of the signal.
            width_i: chosen preset width, 1 to 5.
        Outputs: none.
        """
        # LLFR-00041: store the width in the model, then redraw.
        plot = self.workspace.find_plot(plot_id_i)
        if plot is None:
            return
        # LLFR-00140: changing a width is undoable; choosing the width
        # the curve already has changes nothing and is not recorded.
        snapshot = self.take_snapshot()
        try:
            plot.set_curve_width(signal_name_str, width_i)
        except ValueError:
            # LLFR-00041: not a preset width or not a curve of the plot.
            return
        self.record_undo(snapshot)
        self.redraw_plot(plot)

    def on_plot_delete(self, plot_id_i: int) -> None:
        """Delete a plot and all its curves.

        Inputs:
            plot_id_i: id of the plot.
        Outputs: none.
        """
        # LLFR-00140: deleting a plot is undoable.
        snapshot = self.take_snapshot()
        # LLFR-00049: remove the plot from the model and the view.
        # LLFR-00205: when it is the last plot of all, the model deletes
        # every vertical marker too, in this same undoable action.
        if not self.workspace.delete_plot(plot_id_i):
            return
        self.record_undo(snapshot)
        # LLFR-00167: a first point in the deleted plot is discarded.
        self.discard_pending_delta_if_gone()
        # LLFR-00050: the tab page resizes the remaining plots.
        self.view.remove_plot_view(plot_id_i)
        # LLFR-00180: it may have been the last plot of all.
        self.forget_range_without_plots()

    def on_time_range_changed(self, plot_id_i: int, start_s: float,
                              end_s: float) -> None:
        """Apply a plot's new time range to every plot of every tab.

        Inputs:
            plot_id_i: id of the plot whose range the user changed.
            start_s: start of the range, in seconds.
            end_s: end of the range, in seconds.
        Outputs: none. An unknown plot or a range that is not finite
            is ignored. For a frequency plot, the range is in Hz and is
            kept for that plot only.
        """
        plot = self.workspace.find_plot(plot_id_i)
        if plot is None:
            return
        start_s = float(start_s)
        end_s = float(end_s)
        if not (math.isfinite(start_s) and math.isfinite(end_s)):
            return
        # LLFR-00258: a zoom or a pan of a frequency plot changes only
        # that plot; the view already shows it there.
        if plot.is_frequency_plot():
            plot.set_frequency_range(start_s, end_s)
            return
        # LLFR-00070: all time plots in all tabs share the x-axis range,
        # hidden tabs included. The view's set_plot_time_range does not
        # report back, so there is no loop. LLFR-00180: kept for the
        # time plots created later.
        self.shared_time_range_tuple = (start_s, end_s)
        for other_plot in self.time_plot_list():
            if other_plot is not plot:
                self.view.set_plot_time_range(other_plot.plot_id_i,
                                              start_s, end_s)

    def file_time_range_tuple(self) -> tuple:
        """Return the whole time range of the open file.

        Inputs: none.
        Outputs: a tuple (start_s, end_s) from the first to the last time
            sample, or () when no file is open or it has no finite time.
        """
        # LLFR-00115: the range of the time signal (HLFR-00006).
        if self.signal_file is None:
            return ()
        time_array = np.asarray(self.signal_file.time_array, dtype=float)
        time_array = time_array[np.isfinite(time_array)]
        if time_array.size == 0:
            return ()
        return (float(np.min(time_array)), float(np.max(time_array)))

    def time_plot_range_tuple(self) -> tuple:
        """Return the time range shown by the time plots.

        Inputs: none.
        Outputs: the x-axis range (start_s, end_s) shared by the time
            plots (LLFR-00070), or the whole time range of the file when
            no time plot exists or the plots show the whole range; ()
            when no file is open.
        """
        # LLFR-00248: the range an FFT is computed from; only the time
        # plots count (LLFR-00258: frequency plots have no time range).
        if self.time_plot_list() and self.shared_time_range_tuple:
            return tuple(self.shared_time_range_tuple)
        return self.file_time_range_tuple()

    def on_reset_zoom(self) -> None:
        """Show the whole range in every plot of every tab.

        Inputs: none.
        Outputs: none. Time plots show the whole time range of the file,
            frequency plots their whole frequency range.
        """
        # LLFR-00115: every time plot in every tab; the view fits each
        # y-axis to the new range (LLFR-00076). LLFR-00070, LLFR-00180:
        # the whole range is now the shared one, also for new plots.
        range_tuple = self.file_time_range_tuple()
        if not range_tuple:
            return
        self.shared_time_range_tuple = ()
        start_s, end_s = range_tuple
        for plot in self.all_plot_list():
            if not plot.is_frequency_plot():
                self.view.set_plot_time_range(plot.plot_id_i, start_s,
                                              end_s)
                continue
            # LLFR-00258: a frequency plot returns to 0 Hz up to the
            # highest frequency of its curves.
            plot.frequency_range_tuple = WHOLE_FREQUENCY_RANGE_TUPLE
            limit_tuple = self.frequency_limit_tuple(plot)
            if limit_tuple:
                self.view.set_plot_time_range(plot.plot_id_i,
                                              *limit_tuple)

    def on_grid_toggled(self, shown_b: bool) -> None:
        """Show or hide the grid on every plot of every tab.

        Inputs:
            shown_b: True when the Grid button asks to show the grid.
        Outputs: none.
        """
        # LLFR-00122, LLFR-00123: all plots, all tabs; LLFR-00125: the
        # view applies the state to new plots too. LLFR-00124: the view
        # shows the Grid button to match. The state is kept when a file
        # replaces another one.
        self.grid_shown_b = bool(shown_b)
        self.view.set_grid_shown(self.grid_shown_b)

    # ----------------------------------------------------------------
    # Plot tools and tips
    # ----------------------------------------------------------------

    def on_plot_tool_changed(self, tool_str: str) -> None:
        """Apply the plot tool chosen in the top panel to every plot.

        Inputs:
            tool_str: the active plot tool (TIP_TOOL_STR, ZOOM_TOOL_STR,
                MARKER_TOOL_STR) or NO_TOOL_STR when none is active.
        Outputs: none. An unknown name is ignored.
        """
        # LLFR-00079: one tool at a time; the view keeps the buttons
        # consistent and reports the tool that is now active.
        if not is_known_plot_tool(tool_str):
            return
        # LLFR-00167: deactivating the Delta X or Delta Y tool, in any
        # way (its button, another tool, the Tip or Shift key),
        # discards the first point and its dot.
        if tool_str != self.plot_tool_str:
            self.discard_pending_delta()
        # LLFR-00002, LLFR-00109: NO_TOOL_STR when the active button was
        # clicked again. LLFR-00042, LLFR-00045, LLFR-00078: the plots
        # react to clicks and hovers according to the tool.
        self.plot_tool_str = tool_str
        self.view.set_plot_tool(tool_str)

    def on_tip_pin(self, plot_id_i: int, signal_name_str: str,
                   time_s: float, value_f: float) -> None:
        """Pin a tip at a point of a curve.

        Inputs:
            plot_id_i: id of the plot.
            signal_name_str: name of the signal whose curve was clicked.
            time_s: x-axis value of the point, in seconds.
            value_f: y-axis value of the point.
        Outputs: none.
        """
        # LLFR-00045: keep the tip in the model and draw it.
        plot = self.workspace.find_plot(plot_id_i)
        if plot is None:
            return
        # LLFR-00140: pinning a tip is undoable.
        snapshot = self.take_snapshot()
        try:
            plot.add_pinned_tip(signal_name_str, float(time_s),
                                float(value_f))
        except ValueError:
            # LLFR-00045: the signal is no longer in the plot.
            return
        self.record_undo(snapshot)
        self.redraw_plot(plot)

    def on_pinned_tip_delete(self, plot_id_i: int, tip_index_i: int) -> None:
        """Remove a pinned tip from a plot.

        Inputs:
            plot_id_i: id of the plot.
            tip_index_i: index of the tip in the list last drawn.
        Outputs: none.
        """
        # LLFR-00047: remove the chosen pinned tip, then redraw.
        plot = self.workspace.find_plot(plot_id_i)
        if plot is None:
            return
        if not 0 <= tip_index_i < len(plot.pinned_tip_list):
            return
        # LLFR-00140: deleting a pinned tip is undoable.
        snapshot = self.take_snapshot()
        plot.remove_pinned_tip(plot.pinned_tip_list[tip_index_i])
        self.record_undo(snapshot)
        self.redraw_plot(plot)

    def on_plot_pinned_tips_delete(self, plot_id_i: int) -> None:
        """Remove every pinned tip of one plot.

        Inputs:
            plot_id_i: id of the plot where "Delete all data tips in this
                plot" was chosen.
        Outputs: none. An unknown plot is ignored.
        """
        # LLFR-00412: every tip of this plot, as ONE undoable action
        # (LLFR-00140), with no confirmation and no message; the other
        # plots keep their tips.
        plot = self.workspace.find_plot(plot_id_i)
        if plot is None:
            return
        snapshot = self.take_snapshot()
        if not plot.remove_all_pinned_tips():
            return
        self.record_undo(snapshot)
        self.redraw_plot(plot)

    def on_all_pinned_tips_delete(self, plot_id_i: int) -> None:
        """Remove every pinned tip of every plot of every tab.

        Inputs:
            plot_id_i: id of the plot where "Delete all data tips in all
                plots" was chosen.
        Outputs: none. An unknown plot is ignored.
        """
        # LLFR-00413: time plots and frequency plots of every tab, as ONE
        # undoable action (LLFR-00140), with no confirmation or message.
        if self.workspace.find_plot(plot_id_i) is None:
            return
        changed_plot_list = [plot for plot in self.all_plot_list()
                             if plot.pinned_tip_list]
        snapshot = self.take_snapshot()
        if not self.workspace.remove_all_pinned_tips():
            return
        self.record_undo(snapshot)
        for plot in changed_plot_list:
            self.redraw_plot(plot)

    def on_pinned_tip_move(self, plot_id_i: int, tip_index_i: int,
                           offset_x_f: float, offset_y_f: float) -> None:
        """Keep a pinned tip's label where the user dragged it.

        Inputs:
            plot_id_i: id of the plot.
            tip_index_i: index of the tip in the list last drawn.
            offset_x_f: new offset, in points, from the tip's point to
                the center of its label, to the right.
            offset_y_f: the same offset, upwards.
        Outputs: none. An unknown plot or tip, or an offset that is not
            finite, is ignored.
        """
        # LLFR-00152: the label stays where the button was released; the
        # tip keeps showing the values of the same point (HLFR-00041).
        plot = self.workspace.find_plot(plot_id_i)
        if plot is None:
            return
        if not 0 <= tip_index_i < len(plot.pinned_tip_list):
            return
        # LLFR-00140: moving a pinned tip is undoable; a drag that ends
        # where it started changes nothing and is not recorded.
        snapshot = self.take_snapshot()
        try:
            plot.move_pinned_tip(plot.pinned_tip_list[tip_index_i],
                                 (offset_x_f, offset_y_f))
        except (TypeError, ValueError):
            # LLFR-00152: an offset that cannot be drawn changes nothing.
            return
        self.record_undo(snapshot)
        self.redraw_plot(plot)

    # ----------------------------------------------------------------
    # Text notes
    # ----------------------------------------------------------------

    def on_text_note_create(self, plot_id_i: int, text_str: str,
                            time_s: float, value_f: float) -> None:
        """Write a text note confirmed in the text field of a plot.

        Inputs:
            plot_id_i: id of the plot.
            text_str: the typed text.
            time_s: x-axis value of the clicked point (s, or Hz on a
                frequency plot).
            value_f: y-axis value of the clicked point.
        Outputs: none. A blank text, an unknown plot or a place that is
            not finite writes nothing and shows no message.
        """
        # LLFR-00333: the field stays open when the Text tool is
        # deactivated while typing, so the tool is not checked here.
        plot = self.workspace.find_plot(plot_id_i)
        if plot is None:
            return
        # LLFR-00140: creating a text note is undoable.
        snapshot = self.take_snapshot()
        try:
            # LLFR-00334: a blank text creates nothing, silently.
            text_note = plot.add_text_note(str(text_str), time_s, value_f)
        except (TypeError, ValueError):
            return
        if text_note is None:
            return
        self.record_undo(snapshot)
        self.show_text_notes(plot)

    def on_text_note_move(self, plot_id_i: int, note_index_i: int,
                          time_s: float, value_f: float) -> None:
        """Attach a dragged text note to the place where it was dropped.

        Inputs:
            plot_id_i: id of the plot.
            note_index_i: index of the note in the list last drawn.
            time_s: x-axis value of the drop place (s, or Hz).
            value_f: y-axis value of the drop place.
        Outputs: none. An unknown plot or note, or a place that is not
            finite, changes nothing.
        """
        # LLFR-00339: with any plot tool or none.
        plot = self.workspace.find_plot(plot_id_i)
        if plot is None:
            return
        # LLFR-00140: moving a text note is undoable; a drop at the same
        # place changes nothing and is not recorded.
        snapshot = self.take_snapshot()
        try:
            moved_b = plot.move_text_note(note_index_i, time_s, value_f)
        except (TypeError, ValueError):
            moved_b = False
        if moved_b:
            self.record_undo(snapshot)
        # LLFR-00339: the view shows the note where the model keeps it.
        self.show_text_notes(plot)

    def on_text_note_edit(self, plot_id_i: int, note_index_i: int,
                          text_str: str) -> None:
        """Give a text note the text typed after "Edit".

        Inputs:
            plot_id_i: id of the plot.
            note_index_i: index of the note in the list last drawn.
            text_str: the typed text.
        Outputs: none. A blank text keeps the previous one and shows no
            message.
        """
        # LLFR-00342: let the user change the text of the note.
        plot = self.workspace.find_plot(plot_id_i)
        if plot is None:
            return
        # LLFR-00140: editing a text note is undoable; the same text
        # again changes nothing and is not recorded.
        snapshot = self.take_snapshot()
        if plot.edit_text_note(note_index_i, str(text_str)):
            self.record_undo(snapshot)
        # LLFR-00342: the note shows its kept text in every case.
        self.show_text_notes(plot)

    def on_text_note_delete(self, plot_id_i: int,
                            note_index_i: int) -> None:
        """Remove a text note from a plot.

        Inputs:
            plot_id_i: id of the plot.
            note_index_i: index of the note in the list last drawn.
        Outputs: none.
        """
        # LLFR-00343: "Delete" in the text note menu.
        plot = self.workspace.find_plot(plot_id_i)
        if plot is None:
            return
        # LLFR-00140: deleting a text note is undoable.
        snapshot = self.take_snapshot()
        if not plot.remove_text_note(note_index_i):
            return
        self.record_undo(snapshot)
        self.show_text_notes(plot)

    def on_text_note_size(self, plot_id_i: int, note_index_i: int,
                          size_i: int) -> None:
        """Give a text note the size chosen in its "Size" option.

        Inputs:
            plot_id_i: id of the plot.
            note_index_i: index of the note in the list last drawn.
            size_i: the chosen size in points (LLFR-00385).
        Outputs: none. An unknown plot or note, a size that is not a
            preset, or the note's current size changes nothing.
        """
        # LLFR-00385: draw the text at the chosen size.
        plot = self.workspace.find_plot(plot_id_i)
        if plot is None:
            return
        # LLFR-00140: changing a text note's size is undoable.
        snapshot = self.take_snapshot()
        if not plot.set_text_note_size(note_index_i, size_i):
            return
        self.record_undo(snapshot)
        self.show_text_notes(plot)

    def pick_text_note_color(self, plot_id_i: int, note_index_i: int,
                             part_str: str,
                             chosen_color_str: str = "") -> None:
        """Open the color picker for the border or the text of a note.

        Inputs:
            plot_id_i: id of the plot.
            note_index_i: index of the note in the list last drawn.
            part_str: "border" or "text".
            chosen_color_str: a recent color chosen in the submenu
                (LLFR-00419), or "" to open the picker.
        Outputs: none. A cancelled picker, an unknown plot or note, or
            the color the part already has changes nothing.
        """
        # LLFR-00387: "Border color" and "Text color" open the picker.
        plot = self.workspace.find_plot(plot_id_i)
        if plot is None or not plot.has_text_note_index(note_index_i):
            return
        text_note = plot.text_note_list[note_index_i]
        if part_str == "border":
            current_color_str = text_note.border_color_str
            apply_color = plot.set_text_note_border_color
        else:
            current_color_str = text_note.text_color_str
            apply_color = plot.set_text_note_text_color
        # LLFR-00389: the picker starts at the part's current color.
        # LLFR-00390: one undoable action on confirm, nothing on cancel.
        if self.apply_picked_color(
                current_color_str,
                lambda color_str: apply_color(note_index_i, color_str),
                chosen_color_str):
            self.show_text_notes(plot)

    def on_text_note_border_color(self, plot_id_i: int,
                                  note_index_i: int,
                                  chosen_color_str: str = "") -> None:
        """Let the user pick the border color of a text note.

        Inputs:
            plot_id_i: id of the plot.
            note_index_i: index of the note in the list last drawn.
            chosen_color_str: a recent color chosen in the submenu
                (LLFR-00419), or "" to open the picker.
        Outputs: none.
        """
        # LLFR-00387: "Border color" in the text note menu.
        self.pick_text_note_color(plot_id_i, note_index_i, "border",
                                  chosen_color_str)

    def on_text_note_text_color(self, plot_id_i: int,
                                note_index_i: int,
                                chosen_color_str: str = "") -> None:
        """Let the user pick the text color of a text note.

        Inputs:
            plot_id_i: id of the plot.
            note_index_i: index of the note in the list last drawn.
            chosen_color_str: a recent color chosen in the submenu
                (LLFR-00419), or "" to open the picker.
        Outputs: none.
        """
        # LLFR-00387: "Text color" in the text note menu.
        self.pick_text_note_color(plot_id_i, note_index_i, "text",
                                  chosen_color_str)

    def apply_picked_color(self, current_color_str: str, apply_color,
                           chosen_color_str: str = "") -> bool:
        """Apply a recent color, or the color confirmed in the picker.

        Inputs:
            current_color_str: the item's current color, "#rrggbb",
                shown as chosen when the picker opens (LLFR-00389).
            apply_color: function(color_str) -> bool that changes the
                model and tells whether anything changed.
            chosen_color_str: the recent color the user chose in the
                color submenu (LLFR-00419), or "" for "Other color...",
                which opens the shared color picker (LLFR-00388).
        Outputs: True when the item got a new color, as one undoable
            action; False when the picker was cancelled or the confirmed
            or chosen color is the item's current color (nothing is
            recorded).
        """
        # LLFR-00419: a recent color is applied as a confirmed one.
        picked_color_str = chosen_color_str
        if not picked_color_str:
            # LLFR-00388: the same picker for every item; LLFR-00389: it
            # starts at the current color.
            picked_color_str = self.view.ask_color(current_color_str)
        if picked_color_str is None:
            return False
        # LLFR-00390, LLFR-00140: the snapshot is taken after the picker,
        # so it holds the state just before; the same color changes
        # nothing and adds no undoable action.
        snapshot = self.take_snapshot()
        if not apply_color(str(picked_color_str)):
            return False
        self.record_undo(snapshot)
        return True

    def show_text_notes(self, plot) -> None:
        """Draw the text notes of a plot again, and nothing else.

        Inputs:
            plot: the model Plot.
        Outputs: none.
        """
        # LLFR-00337, LLFR-00340: only the notes change, so the curves,
        # tips, markers and the shown range are not drawn again.
        self.view.set_text_notes(plot.plot_id_i,
                                 self.text_note_data_list(plot))

    # ----------------------------------------------------------------
    # Arrows
    # ----------------------------------------------------------------

    def on_arrow_create(self, plot_id_i: int, start_time_s: float,
                        start_value_f: float, end_time_s: float,
                        end_value_f: float) -> None:
        """Keep an arrow drawn on a plot with the Arrow tool.

        Inputs:
            plot_id_i: id of the plot.
            start_time_s: x value of the press point (s, or Hz on a
                frequency plot).
            start_value_f: y value of the press point.
            end_time_s: x value of the release point, the arrowhead.
            end_value_f: y value of the release point.
        Outputs: none. An unknown plot, a value that is not finite or
            two equal ends create nothing and show no message.
        """
        # LLFR-00372: the arrow from the press to the release.
        plot = self.workspace.find_plot(plot_id_i)
        if plot is None:
            return
        # LLFR-00140: drawing an arrow is undoable.
        snapshot = self.take_snapshot()
        try:
            plot.add_arrow(start_time_s, start_value_f, end_time_s,
                           end_value_f)
        except (TypeError, ValueError):
            return
        self.record_undo(snapshot)
        self.show_arrows(plot)

    def on_arrow_change(self, plot_id_i: int, arrow_index_i: int,
                        start_time_s: float, start_value_f: float,
                        end_time_s: float, end_value_f: float) -> None:
        """Give an arrow the ends it was dragged to.

        Inputs:
            plot_id_i: id of the plot.
            arrow_index_i: index of the arrow in the list last drawn.
            start_time_s: new x value of the end without the arrowhead.
            start_value_f: new y value of that end.
            end_time_s: new x value of the arrowhead's end.
            end_value_f: new y value of the arrowhead's end.
        Outputs: none. An unknown plot or arrow, or ends that are not
            finite or equal, change nothing.
        """
        # LLFR-00376: a move; LLFR-00377: a rotation or a stretch. Both
        # with the Arrow tool or with no tool (LLFR-00382).
        plot = self.workspace.find_plot(plot_id_i)
        if plot is None:
            return
        # LLFR-00140: moving, rotating or stretching an arrow is
        # undoable; the same ends again change nothing.
        snapshot = self.take_snapshot()
        try:
            changed_b = plot.set_arrow_ends(arrow_index_i, start_time_s,
                                            start_value_f, end_time_s,
                                            end_value_f)
        except (TypeError, ValueError):
            changed_b = False
        if changed_b:
            self.record_undo(snapshot)
        # LLFR-00376, LLFR-00377: the view shows the arrow where the
        # model keeps it.
        self.show_arrows(plot)

    def on_arrow_color(self, plot_id_i: int, arrow_index_i: int,
                       chosen_color_str: str = "") -> None:
        """Let the user pick the color of an arrow.

        Inputs:
            plot_id_i: id of the plot.
            arrow_index_i: index of the arrow in the list last drawn.
            chosen_color_str: a recent color chosen in the submenu
                (LLFR-00419), or "" to open the picker.
        Outputs: none. A cancelled picker, an unknown plot or arrow, or
            the arrow's current color changes nothing.
        """
        # LLFR-00379: "Color" in the arrow menu opens the shared picker
        # (LLFR-00388) at the arrow's color (LLFR-00389).
        plot = self.workspace.find_plot(plot_id_i)
        if plot is None or not plot.has_arrow_index(arrow_index_i):
            return
        arrow = plot.arrow_list[arrow_index_i]
        # LLFR-00390: one undoable action on confirm, nothing on cancel.
        if self.apply_picked_color(
                arrow.color_str,
                lambda color_str: plot.set_arrow_color(arrow_index_i,
                                                       color_str),
                chosen_color_str):
            self.show_arrows(plot)

    def on_arrow_delete(self, plot_id_i: int, arrow_index_i: int) -> None:
        """Remove an arrow from a plot.

        Inputs:
            plot_id_i: id of the plot.
            arrow_index_i: index of the arrow in the list last drawn.
        Outputs: none.
        """
        # LLFR-00380: "Delete" in the arrow menu.
        plot = self.workspace.find_plot(plot_id_i)
        if plot is None:
            return
        # LLFR-00140: deleting an arrow is undoable.
        snapshot = self.take_snapshot()
        if not plot.remove_arrow(arrow_index_i):
            return
        self.record_undo(snapshot)
        self.show_arrows(plot)

    def show_arrows(self, plot) -> None:
        """Draw the arrows of a plot again, and nothing else.

        Inputs:
            plot: the model Plot.
        Outputs: none.
        """
        # LLFR-00374, LLFR-00375: only the arrows change, so the curves,
        # tips, markers and the shown range are not drawn again.
        self.view.set_arrows(plot.plot_id_i, self.arrow_data_list(plot))

    # ----------------------------------------------------------------
    # Tabs
    # ----------------------------------------------------------------

    def on_add_tab(self) -> None:
        """Add a new tab and select it.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00140: adding a tab is undoable.
        snapshot = self.take_snapshot()
        # LLFR-00026: the "+" button adds a new tab.
        tab = self.workspace.add_tab()
        self.record_undo(snapshot)
        self.view.add_tab_view(tab.tab_id_i, tab.name_str)
        self.view.set_current_tab(tab.tab_id_i)
        # LLFR-00066: with two tabs or more, "Delete" is enabled.
        self.update_tab_delete_enabled()

    def on_delete_tab(self, tab_id_i: int) -> None:
        """Delete a tab and its plots, unless it is the last tab.

        Inputs:
            tab_id_i: id of the tab.
        Outputs: none.
        """
        # LLFR-00140: deleting a tab is undoable.
        snapshot = self.take_snapshot()
        # LLFR-00066: the model refuses to delete the last tab.
        # LLFR-00205: when its plots were the last ones, the model
        # deletes every vertical marker too, in this same action.
        if not self.workspace.delete_tab(tab_id_i):
            return
        self.record_undo(snapshot)
        # LLFR-00167: a first point in a deleted plot is discarded.
        self.discard_pending_delta_if_gone()
        # LLFR-00028: remove the tab and its plots from the view.
        self.view.remove_tab_view(tab_id_i)
        # LLFR-00180: its plots may have been the last ones.
        self.forget_range_without_plots()
        self.update_tab_delete_enabled()

    def on_rename_tab(self, tab_id_i: int, new_name_str: str) -> None:
        """Rename a tab with the name typed by the user.

        Inputs:
            tab_id_i: id of the tab.
            new_name_str: the typed name.
        Outputs: none.
        """
        # LLFR-00211: another tab's name (compared without surrounding
        # spaces) keeps the previous name and tells the user; nothing
        # changed, so no undo step is recorded (LLFR-00140).
        if self.workspace.is_tab_name_taken(str(new_name_str), tab_id_i):
            self.view.show_tab_name_taken_notification(
                str(new_name_str).strip())
            return
        # LLFR-00140: renaming a tab is undoable; the same name again
        # changes nothing and is not recorded.
        snapshot = self.take_snapshot()
        # LLFR-00067: an empty or blank name keeps the old name, with no
        # message.
        if not self.workspace.rename_tab(tab_id_i, str(new_name_str)):
            return
        self.record_undo(snapshot)
        # LLFR-00030: show the new name (without surrounding spaces).
        tab = self.workspace.find_tab(tab_id_i)
        self.view.rename_tab_view(tab_id_i, tab.name_str)

    # ----------------------------------------------------------------
    # Vertical markers
    # ----------------------------------------------------------------

    def on_marker_place(self, plot_id_i: int, time_s: float) -> None:
        """Place a new vertical marker at a clicked time, on every plot.

        Inputs:
            plot_id_i: id of the clicked plot.
            time_s: time of the clicked point, in seconds.
        Outputs: none. Ignored when the Vertical marker tool is not
            active, the plot is unknown or the time is not finite.
        """
        # LLFR-00081: only while the Vertical marker button is active.
        if self.plot_tool_str != MARKER_TOOL_STR:
            return
        plot = self.workspace.find_plot(plot_id_i)
        if plot is None or not math.isfinite(float(time_s)):
            return
        # LLFR-00259: a click on a frequency plot places no marker.
        if plot.is_frequency_plot():
            return
        # LLFR-00140: placing a marker is undoable.
        snapshot = self.take_snapshot()
        # LLFR-00085, LLFR-00111: the model names it "Flag N" and
        # never reuses N. LLFR-00109: the tool stays active.
        # LLFR-00205: one marker, shown on every plot of every tab.
        self.workspace.add_marker(float(time_s))
        self.record_undo(snapshot)
        self.show_markers()

    def on_marker_move(self, plot_id_i: int, marker_id_i: int,
                       time_s: float) -> None:
        """Leave a dragged vertical marker at the time of the release.

        Inputs:
            plot_id_i: id of the plot the marker was dragged on.
            marker_id_i: id of the dragged marker.
            time_s: time where the mouse button was released, in s.
        Outputs: none. Ignored when a plot tool other than the Flag
            tool is active, an id is unknown or the time is not finite.
        """
        # LLFR-00086, LLFR-00382: dragging works while the Flag button is
        # active or no plot tool is; LLFR-00384: never with another tool.
        if self.plot_tool_str not in (MARKER_TOOL_STR, NO_TOOL_STR):
            return
        plot = self.workspace.find_plot(plot_id_i)
        if plot is None or not math.isfinite(float(time_s)):
            return
        # LLFR-00259: a frequency plot shows no marker to drag.
        if plot.is_frequency_plot():
            return
        # LLFR-00140: moving a marker is undoable; a drag that ends where
        # it started changes nothing and is not recorded.
        snapshot = self.take_snapshot()
        if not self.workspace.move_marker(marker_id_i, float(time_s)):
            return
        self.record_undo(snapshot)
        # LLFR-00092, LLFR-00205: every plot, the other tabs included,
        # shows the marker and its time at the new place.
        self.show_markers()

    def on_marker_rename(self, plot_id_i: int, marker_id_i: int) -> None:
        """Ask the user for a new marker name and show it on every plot.

        Inputs:
            plot_id_i: id of the plot where "Rename" was chosen.
            marker_id_i: id of the marker whose "Rename" was chosen.
        Outputs: none. A cancelled dialog or an empty name changes
            nothing and shows no message.
        """
        # LLFR-00088: let the user type the name, starting from the
        # current one.
        if self.workspace.find_plot(plot_id_i) is None:
            return
        marker = self.workspace.find_marker(marker_id_i)
        if marker is None:
            return
        new_name_str = self.view.ask_marker_name(marker.name_str)
        if new_name_str is None:
            return
        # LLFR-00140: renaming a marker is undoable; the snapshot is
        # taken after the dialog, so it holds the state just before.
        snapshot = self.take_snapshot()
        # LLFR-00089: a blank name keeps the old one, with no message;
        # a marker deleted meanwhile is not renamed.
        if not self.workspace.rename_marker(marker_id_i,
                                            str(new_name_str)):
            return
        self.record_undo(snapshot)
        # LLFR-00112, LLFR-00205: every label shows the new name.
        self.show_markers()

    def on_marker_color(self, plot_id_i: int, marker_id_i: int,
                        chosen_color_str: str = "") -> None:
        """Let the user pick a flag's color and show it on every plot.

        Inputs:
            plot_id_i: id of the plot where "Color" was chosen.
            marker_id_i: id of the flag whose "Color" was chosen.
            chosen_color_str: a recent color chosen in the submenu
                (LLFR-00419), or "" to open the picker.
        Outputs: none. A cancelled picker or the flag's current color
            changes nothing and records nothing.
        """
        # LLFR-00392: "Color" in the flag menu opens the picker
        # (LLFR-00388) at the flag's color (LLFR-00389).
        if self.workspace.find_plot(plot_id_i) is None:
            return
        marker = self.workspace.find_marker(marker_id_i)
        if marker is None:
            return
        if self.apply_picked_color(
                marker.color_str,
                lambda color_str: self.workspace.set_marker_color(
                    marker_id_i, color_str),
                chosen_color_str):
            # LLFR-00392, LLFR-00205: the line, label and time in the new
            # color on every time plot of every tab.
            self.show_markers()

    def on_marker_delete(self, plot_id_i: int, marker_id_i: int) -> None:
        """Remove a vertical marker and its label from every plot.

        Inputs:
            plot_id_i: id of the plot where "Delete" was chosen.
            marker_id_i: id of the marker whose "Delete" was chosen.
        Outputs: none.
        """
        # LLFR-00140: deleting a marker is undoable.
        if self.workspace.find_plot(plot_id_i) is None:
            return
        snapshot = self.take_snapshot()
        # LLFR-00091, LLFR-00205: remove the marker from every plot.
        if not self.workspace.remove_marker(marker_id_i):
            return
        self.record_undo(snapshot)
        self.show_markers()

    def on_all_markers_delete(self, plot_id_i: int) -> None:
        """Remove every flag from every time plot of every tab.

        Inputs:
            plot_id_i: id of the plot where "Delete all flags" was chosen.
        Outputs: none. An unknown plot is ignored.
        """
        # LLFR-00416, LLFR-00205: every flag, with its label and time
        # value, as ONE undoable action (LLFR-00140), with no
        # confirmation and no message.
        if self.workspace.find_plot(plot_id_i) is None:
            return
        snapshot = self.take_snapshot()
        if not self.workspace.remove_all_markers():
            return
        self.record_undo(snapshot)
        self.show_markers()

    # ----------------------------------------------------------------
    # Areas
    # ----------------------------------------------------------------

    def file_limited_span_tuple(self, start_s: float, end_s: float) -> tuple:
        """Return an area span limited to the time range of the file.

        Inputs:
            start_s: one edge of the span, in seconds.
            end_s: the other edge, in seconds.
        Outputs: (start_s, end_s) sorted and cut to the file's time
            range, or () when a time is not finite, no file is open or
            nothing of the span is left.
        """
        # LLFR-00119, LLFR-00312, LLFR-00313: an area stays within the
        # time range of the file.
        start_s = float(start_s)
        end_s = float(end_s)
        if not (math.isfinite(start_s) and math.isfinite(end_s)):
            return ()
        range_tuple = self.file_time_range_tuple()
        if not range_tuple:
            return ()
        start_s, end_s = sorted((start_s, end_s))
        start_s = min(max(start_s, range_tuple[0]), range_tuple[1])
        end_s = min(max(end_s, range_tuple[0]), range_tuple[1])
        if not end_s > start_s:
            return ()
        return (start_s, end_s)

    def moved_span_tuple(self, area, start_s: float, end_s: float) -> tuple:
        """Return the span a moved or resized area takes in the file.

        Inputs:
            area: the model Area before the change.
            start_s: new start sent by the view, in seconds.
            end_s: new end sent by the view, in seconds.
        Outputs: (start_s, end_s) within the file's time range, or ()
            when it cannot be used. A span as wide as the area (a move)
            is shifted into the range, keeping its width; a resized span
            is cut to it.
        """
        # LLFR-00312: a moved area keeps its width and stays within the
        # time range of the file (LLFR-00119).
        start_s = float(start_s)
        end_s = float(end_s)
        range_tuple = self.file_time_range_tuple()
        if not (math.isfinite(start_s) and math.isfinite(end_s)
                and range_tuple):
            return ()
        start_s, end_s = sorted((start_s, end_s))
        width_s = end_s - start_s
        area_width_s = area.end_s - area.start_s
        if (math.isclose(width_s, area_width_s, rel_tol=1e-9, abs_tol=0.0)
                and width_s <= range_tuple[1] - range_tuple[0]):
            start_s = min(max(start_s, range_tuple[0]),
                          range_tuple[1] - width_s)
            return (start_s, start_s + width_s)
        # LLFR-00313: a resized edge is cut to the file's time range.
        return self.file_limited_span_tuple(start_s, end_s)

    def area_time_plot(self, plot_id_i: int, editing_b: bool = False):
        """Return a time plot on which an area may be created or dragged.

        Inputs:
            plot_id_i: id of the plot.
            editing_b: True to move or resize an existing area, which is
                also allowed with no plot tool active; False to create
                one, which needs the Area tool.
        Outputs: the model Plot, or None when the active plot tool does
            not allow it, the plot is unknown or it is a frequency plot.
        """
        # LLFR-00303: an area is created only with the Area tool.
        # LLFR-00312, LLFR-00313, LLFR-00382: it is moved or resized with
        # the Area tool or with no tool. LLFR-00318, LLFR-00384: the
        # other tools never create, move or resize one.
        allowed_tool_tuple = ((AREA_TOOL_STR, NO_TOOL_STR) if editing_b
                              else (AREA_TOOL_STR,))
        if self.plot_tool_str not in allowed_tool_tuple:
            return None
        plot = self.workspace.find_plot(plot_id_i)
        # LLFR-00311: a drag on a frequency plot creates no area.
        if plot is None or plot.is_frequency_plot():
            return None
        return plot

    def on_area_create(self, plot_id_i: int, start_s: float,
                       end_s: float) -> None:
        """Create an area between two times, on every time plot.

        Inputs:
            plot_id_i: id of the plot the area was drawn on.
            start_s: time of the press, in seconds.
            end_s: time of the release, in seconds.
        Outputs: none. Ignored when the Area tool is not active, the plot
            is unknown or a frequency plot, the span is empty or would
            overlap another area.
        """
        # LLFR-00304: the area between the two times.
        if self.area_time_plot(plot_id_i) is None:
            return
        span_tuple = self.file_limited_span_tuple(start_s, end_s)
        if not span_tuple:
            return
        # LLFR-00140: creating an area is undoable.
        snapshot = self.take_snapshot()
        # LLFR-00309: the model names it "Area N" and never reuses N;
        # LLFR-00304: it refuses an overlap. LLFR-00109: the tool stays.
        if self.workspace.add_area(*span_tuple) is None:
            return
        self.record_undo(snapshot)
        # LLFR-00310: one area, shown on every time plot of every tab.
        self.show_areas()

    def on_area_change(self, plot_id_i: int, area_id_i: int,
                       start_s: float, end_s: float) -> None:
        """Leave a moved or resized area where the button was released.

        Inputs:
            plot_id_i: id of the plot the area was dragged on.
            area_id_i: id of the dragged area.
            start_s: new start of the area, in seconds.
            end_s: new end of the area, in seconds.
        Outputs: none. A change that cannot be applied leaves the area
            where it was, and every plot shows it there again.
        """
        # LLFR-00312, LLFR-00313, LLFR-00382: with the Area tool or no
        # tool, on a time plot.
        if self.area_time_plot(plot_id_i, editing_b=True) is None:
            return
        area = self.workspace.find_area(int(area_id_i))
        if area is None:
            return
        span_tuple = self.moved_span_tuple(area, start_s, end_s)
        # LLFR-00140: moving or resizing an area is undoable; a drag that
        # ends where it started changes nothing and is not recorded.
        snapshot = self.take_snapshot()
        if span_tuple:
            # LLFR-00312, LLFR-00313: never over another area.
            self.workspace.set_area_span(int(area_id_i), *span_tuple)
        self.record_undo(snapshot)
        # LLFR-00308, LLFR-00310: every plot, the other tabs included,
        # shows the area and its times where the model keeps it.
        self.show_areas()

    def on_area_rename(self, plot_id_i: int, area_id_i: int) -> None:
        """Ask the user for a new area name and show it on every plot.

        Inputs:
            plot_id_i: id of the plot where "Rename" was chosen.
            area_id_i: id of the area whose "Rename" was chosen.
        Outputs: none. A cancelled dialog or an empty name changes
            nothing and shows no message.
        """
        # LLFR-00315: let the user type the name, starting from the
        # current one, whatever plot tool is active.
        if self.workspace.find_plot(plot_id_i) is None:
            return
        area = self.workspace.find_area(int(area_id_i))
        if area is None:
            return
        new_name_str = self.view.ask_area_name(area.name_str)
        if new_name_str is None:
            return
        # LLFR-00140: renaming an area is undoable; the snapshot is taken
        # after the dialog, so it holds the state just before.
        snapshot = self.take_snapshot()
        # LLFR-00315: a blank name keeps the old one, with no message.
        if not self.workspace.rename_area(int(area_id_i), str(new_name_str)):
            return
        self.record_undo(snapshot)
        # LLFR-00307, LLFR-00310: every label shows the new name.
        self.show_areas()

    def on_area_color(self, plot_id_i: int, area_id_i: int,
                      chosen_color_str: str = "") -> None:
        """Let the user pick an area's color and show it on every plot.

        Inputs:
            plot_id_i: id of the plot where "Color" was chosen.
            area_id_i: id of the area.
            chosen_color_str: a recent color chosen in the submenu
                (LLFR-00419), or "" to open the picker.
        Outputs: none. An unknown plot or area, a cancelled picker or the
            area's current color changes nothing and records nothing.
        """
        # LLFR-00351: with any plot tool, like the other menu options;
        # the shared picker (LLFR-00388) starts at the area's color
        # (LLFR-00389).
        if self.workspace.find_plot(plot_id_i) is None:
            return
        area = self.workspace.find_area(int(area_id_i))
        if area is None:
            return
        # LLFR-00140, LLFR-00390: changing an area's color is undoable.
        if self.apply_picked_color(
                area.color_str,
                lambda color_str: self.workspace.set_area_color(
                    int(area_id_i), color_str),
                chosen_color_str):
            # LLFR-00310, LLFR-00351: every time plot of every tab.
            self.show_areas()

    def on_area_delete(self, plot_id_i: int, area_id_i: int) -> None:
        """Remove an area and its label from every plot.

        Inputs:
            plot_id_i: id of the plot where "Delete" was chosen.
            area_id_i: id of the area whose "Delete" was chosen.
        Outputs: none.
        """
        # LLFR-00140: deleting an area is undoable.
        if self.workspace.find_plot(plot_id_i) is None:
            return
        snapshot = self.take_snapshot()
        # LLFR-00316, LLFR-00310: remove the area from every plot.
        if not self.workspace.remove_area(int(area_id_i)):
            return
        self.record_undo(snapshot)
        self.show_areas()

    def on_all_areas_delete(self, plot_id_i: int) -> None:
        """Remove every area from every time plot of every tab.

        Inputs:
            plot_id_i: id of the plot where "Delete all areas" was chosen.
        Outputs: none. An unknown plot is ignored.
        """
        # LLFR-00417, LLFR-00310: every area, with its label and time
        # values, as ONE undoable action (LLFR-00140), with no
        # confirmation and no message.
        if self.workspace.find_plot(plot_id_i) is None:
            return
        snapshot = self.take_snapshot()
        if not self.workspace.remove_all_areas():
            return
        self.record_undo(snapshot)
        self.show_areas()

    # ----------------------------------------------------------------
    # Delta markers
    # ----------------------------------------------------------------

    def discard_pending_delta(self) -> None:
        """Forget the first point of a delta marker and remove its dot.

        Inputs: none.
        Outputs: none. Does nothing when no first point is picked.
        """
        # LLFR-00167: the first point and its dot go away.
        if not self.pending_delta_tuple:
            return
        plot_id_i = self.pending_delta_tuple[0]
        self.pending_delta_tuple = ()
        self.view.set_delta_first_point(plot_id_i, ())

    def discard_pending_delta_if_gone(self) -> None:
        """Discard the first point when its plot or its curve is gone.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00167, LLFR-00178: a first point can only be kept while
        # its curve is still in its plot.
        if not self.pending_delta_tuple:
            return
        plot_id_i, point_tuple = self.pending_delta_tuple
        plot = self.workspace.find_plot(plot_id_i)
        if plot is None or not plot.has_signal(point_tuple[0]):
            self.discard_pending_delta()

    def on_delta_point_pick(self, plot_id_i: int, signal_name_str: str,
                            time_s: float, value_f: float) -> None:
        """Take a clicked curve sample as a point of a delta marker.

        Inputs:
            plot_id_i: id of the clicked plot.
            signal_name_str: name of the signal of the clicked curve.
            time_s: time of the curve sample nearest to the mouse, in s.
            value_f: value of that sample.
        Outputs: none. Ignored when no delta tool is active, the plot or
            the signal is unknown or the values are not finite.
        """
        # LLFR-00163: only while the Delta X or Delta Y button is active.
        if not is_delta_tool(self.plot_tool_str):
            return
        plot = self.workspace.find_plot(plot_id_i)
        if plot is None or not plot.has_signal(str(signal_name_str)):
            return
        time_s = float(time_s)
        value_f = float(value_f)
        if not (math.isfinite(time_s) and math.isfinite(value_f)):
            return
        point_tuple = (str(signal_name_str), time_s, value_f)
        if (self.pending_delta_tuple
                and self.pending_delta_tuple[0] == plot_id_i):
            self.place_delta_marker(plot, self.pending_delta_tuple[1],
                                    point_tuple)
            return
        # LLFR-00166: a first point in another plot is discarded.
        self.discard_pending_delta()
        # LLFR-00163: the clicked sample is the first point, marked with
        # a dot (LLFR-00172: in the marker color, drawn by the view).
        self.pending_delta_tuple = (plot_id_i, point_tuple)
        self.view.set_delta_first_point(plot_id_i, point_tuple)

    def place_delta_marker(self, plot, first_point_tuple: tuple,
                           second_point_tuple: tuple) -> None:
        """Draw a delta marker between the first and the second point.

        Inputs:
            plot: the model Plot of both points.
            first_point_tuple: (signal_name_str, time_s, value_f).
            second_point_tuple: the same for the second point.
        Outputs: none.
        """
        # LLFR-00164: the kind follows the active button.
        kind_str = (DELTA_X_KIND_STR if self.plot_tool_str == DELTA_X_TOOL_STR
                    else DELTA_Y_KIND_STR)
        # LLFR-00164: the dot of the first point goes away.
        self.discard_pending_delta()
        # LLFR-00140: placing a delta marker is ONE undoable action.
        snapshot = self.take_snapshot()
        try:
            plot.add_delta_marker(kind_str, first_point_tuple,
                                  second_point_tuple)
        except ValueError:
            # LLFR-00164: a point whose curve is gone places nothing.
            return
        self.record_undo(snapshot)
        # LLFR-00109: the tool stays active for the next measurement.
        # LLFR-00168, LLFR-00170: draw the marker.
        self.redraw_plot(plot)

    def on_delta_marker_delete(self, plot_id_i: int,
                               delta_marker_id_i: int) -> None:
        """Remove a delta marker from a plot.

        Inputs:
            plot_id_i: id of the plot.
            delta_marker_id_i: id of the delta marker whose "Delete" was
                chosen.
        Outputs: none. Unknown ids are ignored.
        """
        # LLFR-00140: deleting a delta marker is undoable.
        plot = self.workspace.find_plot(plot_id_i)
        if plot is None:
            return
        snapshot = self.take_snapshot()
        # LLFR-00176: remove it, then draw the plot without it.
        if not plot.remove_delta_marker(int(delta_marker_id_i)):
            return
        self.record_undo(snapshot)
        self.redraw_plot(plot)

    def on_delta_marker_color(self, plot_id_i: int, delta_marker_id_i: int,
                              chosen_color_str: str = "") -> None:
        """Let the user pick the color of one delta marker.

        Inputs:
            plot_id_i: id of the plot.
            delta_marker_id_i: id of the delta marker whose "Color" was
                chosen.
            chosen_color_str: a recent color chosen in the submenu
                (LLFR-00419), or "" to open the picker.
        Outputs: none. An unknown plot or delta marker, a cancelled
            picker or the marker's current color changes nothing and
            records nothing.
        """
        # LLFR-00409: "Color" in the delta marker menu opens the shared
        # picker (LLFR-00388) at the marker's color (LLFR-00389).
        plot = self.workspace.find_plot(plot_id_i)
        if plot is None:
            return
        delta_marker = plot.find_delta_marker(int(delta_marker_id_i))
        if delta_marker is None:
            return
        # LLFR-00140, LLFR-00390: changing a delta marker's color is one
        # undoable action; the points, the value and the other delta
        # markers stay as they are.
        if self.apply_picked_color(
                delta_marker.color_str,
                lambda color_str: plot.set_delta_marker_color(
                    int(delta_marker_id_i), color_str),
                chosen_color_str):
            self.redraw_plot(plot)

    def on_plot_delta_markers_delete(self, plot_id_i: int) -> None:
        """Remove every delta marker of one plot.

        Inputs:
            plot_id_i: id of the plot where "Delete all delta markers in
                this plot" was chosen.
        Outputs: none. An unknown plot is ignored.
        """
        # LLFR-00414: every Delta X and Delta Y marker of this plot, as
        # ONE undoable action (LLFR-00140), with no confirmation and no
        # message; the other plots and a picked first point (LLFR-00163,
        # pending_delta_tuple) do not change.
        plot = self.workspace.find_plot(plot_id_i)
        if plot is None:
            return
        snapshot = self.take_snapshot()
        if not plot.remove_all_delta_markers():
            return
        self.record_undo(snapshot)
        self.redraw_plot(plot)

    def on_all_delta_markers_delete(self, plot_id_i: int) -> None:
        """Remove every delta marker of every plot of every tab.

        Inputs:
            plot_id_i: id of the plot where "Delete all delta markers in
                all plots" was chosen.
        Outputs: none. An unknown plot is ignored.
        """
        # LLFR-00415: time plots and frequency plots of every tab, as ONE
        # undoable action (LLFR-00140), with no confirmation or message;
        # a picked first point (LLFR-00163) does not change.
        if self.workspace.find_plot(plot_id_i) is None:
            return
        changed_plot_list = [plot for plot in self.all_plot_list()
                             if plot.delta_marker_list]
        snapshot = self.take_snapshot()
        if not self.workspace.remove_all_delta_markers():
            return
        self.record_undo(snapshot)
        for plot in changed_plot_list:
            self.redraw_plot(plot)

    # ----------------------------------------------------------------
    # Undo and redo
    # ----------------------------------------------------------------

    def on_undo(self) -> None:
        """Reverse the most recent undoable action not undone yet.

        Inputs: none.
        Outputs: none. Does nothing when no action is left to undo.
        """
        # LLFR-00141: with nothing to undo, the button and the shortcut
        # do nothing.
        if not self.undo_history.can_undo():
            self.update_undo_enabled()
            return
        # LLFR-00138: return the model to the state before the action;
        # LLFR-00192: the state after it is kept for redo.
        snapshot = self.undo_history.undo(self.take_snapshot())
        self.show_restored_snapshot(snapshot)

    def on_redo(self) -> None:
        """Reapply the most recently undone action not redone yet.

        Inputs: none.
        Outputs: none. Does nothing when no undone action is left.
        """
        # LLFR-00194: with nothing to redo, the button and the shortcut
        # do nothing.
        if not self.undo_history.can_redo():
            self.update_undo_enabled()
            return
        # LLFR-00192: return the model to the state after the undone
        # action, and make the action available to undo again.
        snapshot = self.undo_history.redo(self.take_snapshot())
        self.show_restored_snapshot(snapshot)

    def show_restored_snapshot(self, snapshot) -> None:
        """Restore a saved state and rebuild every view from it.

        Inputs:
            snapshot: the WorkspaceSnapshot taken out of the history by
                an undo or a redo.
        Outputs: none.
        """
        shown_tab_id_i = self.view.current_tab_id()
        # LLFR-00167: the views are rebuilt, so a first point is
        # discarded (it is not part of any snapshot).
        self.discard_pending_delta()
        # LLFR-00258, LLFR-00140 Note: zooms are not undoable, so each
        # frequency plot that is still there keeps the range it shows.
        frequency_range_dict = {
            plot.plot_id_i: plot.frequency_range_tuple
            for plot in self.all_plot_list() if plot.is_frequency_plot()}
        # LLFR-00138, LLFR-00192: the model takes the saved state.
        self.workspace.restore(snapshot)
        for plot in self.all_plot_list():
            if plot.is_frequency_plot() and (
                    plot.plot_id_i in frequency_range_dict):
                plot.frequency_range_tuple = frequency_range_dict[
                    plot.plot_id_i]
        # LLFR-00141, LLFR-00194: the buttons follow the history.
        self.update_undo_enabled()
        # LLFR-00138, LLFR-00192: select the tab that was selected in the
        # saved state, or else the tab selected now, or else the first.
        current_tab_id_i = snapshot.current_tab_id_i
        if self.workspace.find_tab(current_tab_id_i) is None:
            current_tab_id_i = shown_tab_id_i
        # LLFR-00070, LLFR-00140 Note: the shared range is view state and
        # is kept; LLFR-00180: with no plot left, it is the whole range.
        self.forget_range_without_plots()
        self.rebuild_all_views(current_tab_id_i)

    def rebuild_all_views(self, current_tab_id_i: int) -> None:
        """Show every tab, plot, curve, tip and marker of the workspace.

        Inputs:
            current_tab_id_i: id of the tab to select; the first tab is
                selected when no tab has that id.
        Outputs: none. Every plot shows the shared time range.
        """
        # LLFR-00138: the view shows the restored model, from scratch.
        self.view.clear_tab_views()
        for tab in self.workspace.tab_list:
            self.view.add_tab_view(tab.tab_id_i, tab.name_str)
        for tab in self.workspace.tab_list:
            for plot in tab.plot_list:
                # LLFR-00069: the plots in their order, top to bottom;
                # LLFR-00256: each with its kind.
                self.view.add_plot_view(tab.tab_id_i, plot.plot_id_i,
                                        plot.kind_str)
                # LLFR-00068: time on the x-axis; LLFR-00070,
                # LLFR-00180: then the range shared by all plots.
                self.redraw_plot(plot)
        # LLFR-00138: select the tab of the state before the action.
        if self.workspace.find_tab(current_tab_id_i) is None:
            current_tab_id_i = self.workspace.tab_list[0].tab_id_i
        self.view.set_current_tab(current_tab_id_i)
        # LLFR-00066: "Delete" only when more than one tab is left.
        self.update_tab_delete_enabled()

    # ----------------------------------------------------------------
    # Synthetic signals
    # ----------------------------------------------------------------

    def rename_signal(self, old_name_str: str, new_name_str: str) -> None:
        """Show a renamed synthetic signal under its new name.

        Inputs:
            old_name_str: the previous name of the signal.
            new_name_str: its new name.
        Outputs: none. The rename is not an undoable action and keeps
            the undo and redo history, whose saved states are renamed
            too, so that an undo or a redo draws the curve under its
            new name.
        """
        # LLFR-00266: not undoable; the history is kept, with the new
        # name in every saved state.
        for snapshot in self.undo_history.saved_snapshot_list():
            snapshot.rename_signal(old_name_str, new_name_str)
        # LLFR-00163: a first point on the curve keeps its point.
        if self.pending_delta_tuple:
            plot_id_i, point_tuple = self.pending_delta_tuple
            if point_tuple[0] == old_name_str:
                self.pending_delta_tuple = (
                    plot_id_i, (new_name_str,) + tuple(point_tuple[1:]))
                self.view.set_delta_first_point(
                    plot_id_i, self.pending_delta_tuple[1])
        if not self.workspace.rename_signal(old_name_str, new_name_str):
            return
        # LLFR-00266: every legend that shows the signal shows the new
        # name; the other plots are not drawn again.
        for plot in self.all_plot_list():
            if plot.has_signal(new_name_str):
                self.redraw_plot(plot)

    def remove_signals(self, signal_name_list: list) -> None:
        """Remove the curves of deleted synthetic signals from every plot.

        Inputs:
            signal_name_list: the names of the deleted signals.
        Outputs: none. The plots left with no curve are deleted, and
            the undo and redo history is cleared.
        """
        # LLFR-00255: the curves leave every plot; LLFR-00051: an
        # emptied plot is deleted; LLFR-00205: with no plot left, the
        # vertical markers are deleted too.
        removed_name_set = set(signal_name_list)
        changed_plot_list = [
            plot for plot in self.all_plot_list()
            if any(plot.has_signal(name_str)
                   for name_str in removed_name_set)]
        deleted_plot_id_list = self.workspace.remove_signal_curves(
            removed_name_set)
        # LLFR-00167: a first point on a removed curve is discarded.
        self.discard_pending_delta_if_gone()
        # LLFR-00255: the undo and redo history is cleared; deleting a
        # synthetic signal is not undoable (LLFR-00140).
        self.undo_history.clear()
        self.update_undo_enabled()
        # LLFR-00050, LLFR-00180: the other plots fill the space, and
        # with no plot left a new plot shows the whole range.
        for plot_id_i in deleted_plot_id_list:
            self.view.remove_plot_view(plot_id_i)
        self.forget_range_without_plots()
        # LLFR-00255: the plots that keep other curves are drawn again.
        for plot in changed_plot_list:
            if plot.plot_id_i not in deleted_plot_id_list:
                self.redraw_plot(plot)

    # ----------------------------------------------------------------
    # Layout files
    # ----------------------------------------------------------------

    def layout_time_range_tuple(self) -> tuple:
        """Return the time range shared by the plots, in seconds.

        Inputs: none.
        Outputs: (start_s, end_s): the shared range, or the whole time
            range of the file when no plot is zoomed; () when no file is
            open.
        """
        # LLFR-00225 item 4, LLFR-00070: the range every plot shows.
        if self.shared_time_range_tuple:
            return tuple(self.shared_time_range_tuple)
        return self.file_time_range_tuple()

    def layout_dict(self, panel_width_tuple: tuple = (),
                    synthetic_signal_list: list = ()) -> dict:
        """Return the content of a layout file for the current layout.

        Inputs:
            panel_width_tuple: (plot panel width, signal list panel
                width) in pixels, or () when unknown.
            synthetic_signal_list: the entries of the synthetic signals
                (LLFR-00225 item 10, issue #110).
        Outputs: the dict of model.layout_file.build_layout_dict.
        """
        # LLFR-00225: tabs, shown tab, plots, curves, range, grid,
        # markers, data tips, delta markers and panel widths.
        # LLFR-00226: no file name, history, plot tool or search text.
        return build_layout_dict(
            self.workspace, self.view.current_tab_id(),
            self.layout_time_range_tuple(), self.grid_shown_b,
            panel_width_tuple, synthetic_signal_list)

    def load_layout(self, layout_dict: dict,
                    synthetic_signal_builder=None,
                    synthetic_signal_restore_function=None):
        """Rebuild the layout of a layout file and show it.

        Inputs:
            layout_dict: the content of the file
                (model.layout_file.parse_layout_text).
            synthetic_signal_builder: optional function that creates the
                synthetic signals of the file (LLFR-00262).
            synthetic_signal_restore_function: optional function without
                arguments that puts back the synthetic signals of before
                the load; called first when the rebuild fails, so that
                the views are redrawn with them (LLFR-00236).
        Outputs: the LayoutResult, whose report says what was not
            rebuilt; None when no data file is open (LLFR-00218).
        """
        # LLFR-00218: a layout needs the signals of a data file.
        if self.signal_file is None:
            return None
        # LLFR-00167: the views are rebuilt, so a first point is
        # discarded.
        self.discard_pending_delta()
        # PCR-00025: an unexpected failure leaves the layout as it was.
        snapshot = self.take_snapshot()
        try:
            # LLFR-00229 to LLFR-00235: rebuild the file's layout.
            result = rebuild_layout(
                self.workspace, layout_dict, self.signal_file.signal_dict,
                self.signal_file.time_array, synthetic_signal_builder)
        except Exception:
            # LLFR-00236: the synthetic signals come back before the
            # views are redrawn, so the old curves find their samples.
            if synthetic_signal_restore_function is not None:
                synthetic_signal_restore_function()
            self.workspace.restore(snapshot)
            self.rebuild_all_views(snapshot.current_tab_id_i)
            raise
        # LLFR-00230, LLFR-00234: the file's time range, limited to the
        # data file, in every plot; LLFR-00180: () is the whole range.
        self.shared_time_range_tuple = tuple(result.time_range_tuple)
        self.forget_range_without_plots()
        # LLFR-00230, LLFR-00122, LLFR-00123: the file's grid setting.
        if result.grid_shown_b is not None:
            self.on_grid_toggled(result.grid_shown_b)
        # LLFR-00238: loading clears the undo and redo history and is not
        # itself undoable.
        self.undo_history.clear()
        self.update_undo_enabled()
        # LLFR-00229: show every tab, and the first tab of the file.
        shown_tab_id_i = result.first_tab_id_i
        if shown_tab_id_i < 0:
            shown_tab_id_i = snapshot.current_tab_id_i
        self.rebuild_all_views(shown_tab_id_i)
        return result
