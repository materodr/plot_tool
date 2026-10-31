"""Plot controller: tabs, plots, curves and tips (HLFR-00012 to 00025).

It keeps the Workspace model and tells the view what to show. It talks
to the view only through plain method calls with plain values (ids,
names, numbers, numpy arrays), so it can be tested with a fake view
(COR-00003, COR-00009). The view must offer:

- tabs: ``add_tab_view``, ``remove_tab_view``, ``rename_tab_view``,
  ``clear_tab_views``, ``set_current_tab``, ``current_tab_id``,
  ``set_tab_delete_enabled``;
- plots: ``add_plot_view``, ``remove_plot_view``, ``draw_plot``,
  ``set_plot_time_range``, ``plot_time_range``, ``set_tip_mode``;
- boxes: ``show_full_tab_notification``;
- handler setters: ``set_signal_double_click_handler``,
  ``set_tip_mode_handler``, ``set_tab_handlers`` and
  ``set_plot_handlers``.

Every handler validates the ids it gets from the view and ignores
unknown ones, so a stale request never raises (PCR-00025).
"""

from model.workspace import Workspace


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
        tip_mode_b: True while the Tip button is active.
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
        self.tip_mode_b = False
        # LLFR-00015, LLFR-00016: reset the tabs for every opened file.
        file_controller.add_file_opened_listener(self.on_file_opened)
        # LLFR-00019, LLFR-00042: signal list and Tip button requests.
        view.set_signal_double_click_handler(self.on_signal_double_clicked)
        view.set_tip_mode_handler(self.on_tip_mode_changed)
        # LLFR-00026, LLFR-00028, LLFR-00030: tab menu and "+" button.
        view.set_tab_handlers(self.on_add_tab, self.on_delete_tab,
                              self.on_rename_tab)
        # LLFR-00021, LLFR-00039, LLFR-00041, LLFR-00045, LLFR-00047,
        # LLFR-00049, LLFR-00070: requests made on a plot.
        view.set_plot_handlers(
            curve_delete_handler=self.on_curve_delete,
            curve_width_handler=self.on_curve_width,
            plot_delete_handler=self.on_plot_delete,
            signal_drop_handler=self.on_signal_dropped,
            tip_pin_handler=self.on_tip_pin,
            pinned_tip_delete_handler=self.on_pinned_tip_delete,
            time_range_handler=self.on_time_range_changed)
        # LLFR-00024: show the tabs of the model (one empty tab).
        self.rebuild_tab_views()

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

    def has_signal(self, signal_name_str: str) -> bool:
        """Tell whether the open file has a signal of that name.

        Inputs:
            signal_name_str: the signal name sent by the view.
        Outputs: True when a file is open and holds the signal.
        """
        # LLFR-00020, LLFR-00021, LLFR-00055: only signals of the open
        # file, Time included, can be drawn.
        if self.signal_file is None:
            return False
        return signal_name_str in self.signal_file.signal_dict

    def curve_data_list(self, plot) -> list:
        """Return the drawing data of every curve of a plot.

        Inputs:
            plot: the model Plot.
        Outputs: a list of tuples (signal_name_str, time_array,
            value_array, color_str, width_i) in curve order.
        """
        # LLFR-00068: every curve is drawn against the time signal.
        time_array = self.signal_file.time_array
        # LLFR-00033, LLFR-00034, LLFR-00041, LLFR-00052: colors and
        # widths come from the model.
        return [(curve.signal_name_str, time_array,
                 self.signal_file.signal_array(curve.signal_name_str),
                 curve.color_str, curve.width_i)
                for curve in plot.curve_list]

    def other_plot_list(self, plot) -> list:
        """Return the other plots in the tab of a plot.

        Inputs:
            plot: the model Plot.
        Outputs: a list of Plot objects, from top to bottom.
        """
        # LLFR-00070: the plots that share the time range with ``plot``.
        tab = self.workspace.tab_of_plot(plot.plot_id_i)
        if tab is None:
            return []
        return [other_plot for other_plot in tab.plot_list
                if other_plot is not plot]

    def redraw_plot(self, plot, new_plot_b: bool = False) -> None:
        """Draw a plot's curves and pinned tips again.

        Inputs:
            plot: the model Plot.
            new_plot_b: True for a plot drawn for the first time.
        Outputs: none. The plot keeps the time range it showed; a new
            plot takes the range of the other plots in its tab.
        """
        # LLFR-00070: the range to keep after the redraw. A new plot
        # takes the range of its tab; an existing one keeps its own.
        if not new_plot_b:
            range_tuple = self.view.plot_time_range(plot.plot_id_i)
        else:
            other_plot_list = self.other_plot_list(plot)
            range_tuple = ()
            if other_plot_list:
                range_tuple = self.view.plot_time_range(
                    other_plot_list[0].plot_id_i)
        # LLFR-00068: time on the x-axis; LLFR-00045: pinned tips.
        pinned_tip_list = [(pinned_tip.signal_name_str, pinned_tip.time_s,
                            pinned_tip.value_f)
                           for pinned_tip in plot.pinned_tip_list]
        self.view.draw_plot(plot.plot_id_i, self.curve_data_list(plot),
                            pinned_tip_list)
        if range_tuple:
            start_s, end_s = range_tuple
            self.view.set_plot_time_range(plot.plot_id_i, start_s, end_s)

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
        # LLFR-00015, LLFR-00016: close all tabs and plots and leave one
        # tab with no plots (also harmless for the first file).
        self.workspace.reset()
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
        # LLFR-00031: a full tab gets no new plot.
        plot = self.workspace.add_plot(tab.tab_id_i)
        if plot is None:
            # LLFR-00032: tell the user to add a tab or delete a plot.
            self.view.show_full_tab_notification()
            return
        # LLFR-00019, LLFR-00069: the new plot goes below the others.
        self.view.add_plot_view(tab.tab_id_i, plot.plot_id_i)
        # LLFR-00020, LLFR-00052: draw the signal with width 1.
        plot.add_curve(signal_name_str)
        self.redraw_plot(plot, new_plot_b=True)

    def on_signal_dropped(self, plot_id_i: int,
                          signal_name_str: str) -> None:
        """Draw a dropped signal in the plot it was dropped on.

        Inputs:
            plot_id_i: id of the plot the signal was dropped on.
            signal_name_str: the dropped signal name.
        Outputs: none.
        """
        # LLFR-00022, LLFR-00023: only a drop on a known plot does
        # anything; there is no other path from a drop to a new plot.
        plot = self.workspace.find_plot(plot_id_i)
        if plot is None or not self.has_signal(signal_name_str):
            return
        # LLFR-00056, LLFR-00057: a signal already shown is not drawn
        # again, and no message is shown.
        if plot.add_curve(signal_name_str) is None:
            return
        # LLFR-00021: draw the signal in that plot.
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
        # LLFR-00039: remove the curve from the plot.
        if not self.workspace.remove_curve(plot_id_i, signal_name_str):
            return
        plot = self.workspace.find_plot(plot_id_i)
        if plot is None:
            # LLFR-00051, LLFR-00049, LLFR-00050: the plot had no curves
            # left and was deleted; the others fill the space.
            self.view.remove_plot_view(plot_id_i)
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
        try:
            plot.set_curve_width(signal_name_str, width_i)
        except ValueError:
            # LLFR-00041: not a preset width or not a curve of the plot.
            return
        self.redraw_plot(plot)

    def on_plot_delete(self, plot_id_i: int) -> None:
        """Delete a plot and all its curves.

        Inputs:
            plot_id_i: id of the plot.
        Outputs: none.
        """
        # LLFR-00049: remove the plot from the model and the view.
        if not self.workspace.delete_plot(plot_id_i):
            return
        # LLFR-00050: the tab page resizes the remaining plots.
        self.view.remove_plot_view(plot_id_i)

    def on_time_range_changed(self, plot_id_i: int, start_s: float,
                              end_s: float) -> None:
        """Apply a plot's new time range to every plot of its tab.

        Inputs:
            plot_id_i: id of the plot whose range the user changed.
            start_s: start of the range, in seconds.
            end_s: end of the range, in seconds.
        Outputs: none.
        """
        # LLFR-00070: the plots of a tab share the x-axis range. The
        # view's set_plot_time_range does not report back, so there is
        # no loop.
        plot = self.workspace.find_plot(plot_id_i)
        if plot is None:
            return
        for other_plot in self.other_plot_list(plot):
            self.view.set_plot_time_range(other_plot.plot_id_i, start_s,
                                          end_s)

    # ----------------------------------------------------------------
    # Tips
    # ----------------------------------------------------------------

    def on_tip_mode_changed(self, enabled_b: bool) -> None:
        """Turn hover tips on or off in every plot.

        Inputs:
            enabled_b: True when the Tip button became active.
        Outputs: none.
        """
        # LLFR-00042: hover tips only while the Tip button is active.
        self.tip_mode_b = bool(enabled_b)
        self.view.set_tip_mode(self.tip_mode_b)

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
        try:
            plot.add_pinned_tip(signal_name_str, float(time_s),
                                float(value_f))
        except ValueError:
            # LLFR-00045: the signal is no longer in the plot.
            return
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
        plot.remove_pinned_tip(plot.pinned_tip_list[tip_index_i])
        self.redraw_plot(plot)

    # ----------------------------------------------------------------
    # Tabs
    # ----------------------------------------------------------------

    def on_add_tab(self) -> None:
        """Add a new tab and select it.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00026: the "+" button adds a new tab.
        tab = self.workspace.add_tab()
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
        # LLFR-00066: the model refuses to delete the last tab.
        if not self.workspace.delete_tab(tab_id_i):
            return
        # LLFR-00028: remove the tab and its plots from the view.
        self.view.remove_tab_view(tab_id_i)
        self.update_tab_delete_enabled()

    def on_rename_tab(self, tab_id_i: int, new_name_str: str) -> None:
        """Rename a tab with the name typed by the user.

        Inputs:
            tab_id_i: id of the tab.
            new_name_str: the typed name.
        Outputs: none.
        """
        # LLFR-00067: an empty or blank name keeps the old name, with no
        # message.
        if not self.workspace.rename_tab(tab_id_i, str(new_name_str)):
            return
        # LLFR-00030: show the new name (without surrounding spaces).
        tab = self.workspace.find_tab(tab_id_i)
        self.view.rename_tab_view(tab_id_i, tab.name_str)
