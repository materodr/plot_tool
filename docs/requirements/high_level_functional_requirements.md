# High-Level Functional Requirements

Prefix: `HLFR`. Format rules: see [README.md](README.md).
Rules for creating and changing functional requirements: PCR-00028 to PCR-00031 in [process_of_collaboration.md](process_of_collaboration.md).
The low-level requirements that refine these are in [low_level_functional_requirements.md](low_level_functional_requirements.md).

The requirements are grouped by part of the interface: General, Top panel, Signal list panel and Plot panel.

## General

### HLFR-00001 Interface layout
The app interface must be divided into three panels: a top panel, a plot panel and a signal list panel.

Note: The **top panel** holds the controls for opening a file and for the plot tools. The **plot panel** shows the plots where signal curves are drawn, organized in tabs. The **signal list panel** shows the signals of the opened file, from which the user picks what to plot.

### HLFR-00002 Error notification
When an error occurs, the app must notify the user with an error box that describes the error.

Note: The error box shown when a file cannot be opened is called the **File Open Error box**.

### HLFR-00003 Active button indication
The interface must show which buttons are active.

Note: This applies to every button, including the button that opens a file.

### HLFR-00026 Resize the panels
The user must be able to change the widths of the plot panel and the signal list panel.

### HLFR-00040 Undo
The user must be able to undo their most recent actions on the tabs, plots, curves, tips and markers.


## Top panel

### HLFR-00004 Open a file
The user must be able to open a time series file from the top panel.

### HLFR-00005 Supported file formats
The app must open files in these formats: CSV (`.csv`), Excel (`.xlsx`), MATLAB (`.mat`) and HDF5 (`.h5`, `.hdf5`).

Note: More formats may be added in later versions.

### HLFR-00006 Time signal name
The app must identify the time signal as the signal named `Time`.

### HLFR-00007 Time unit
The app must treat the values of the time signal as seconds.

Note: Files are assumed to always store time in seconds.

### HLFR-00008 Minimum file content
The app must open a file only if it contains a time signal (HLFR-00006) and at least one other signal.

### HLFR-00009 Equal sample count
The app must open a file only if all its signals have the same number of samples.

### HLFR-00010 Replace file confirmation
If the selected file can be opened and another file is already open, the app must ask the user whether to proceed, stating that proceeding will close the current file.

### HLFR-00032 One plot tool at a time
The app must allow only one plot tool to be active at a time.

Note: The **plot tools** are the Tip, Zoom, Vertical marker, Delta X and Delta Y functions. Each one is started from its own button in the top panel.

### HLFR-00042 Button icons
Each button in the top panel must show an icon that illustrates its function.

## Signal list panel

### HLFR-00011 Signal list
The signal list panel must show the names of the signals contained in the opened file.

Note: The updated signal list is the confirmation that the file was opened successfully.

### HLFR-00012 Plot a signal in a new plot
The user must be able to plot a signal from the signal list in a new plot.

### HLFR-00013 Add a signal to an existing plot
The user must be able to add a signal from the signal list to an existing plot.

### HLFR-00033 Search the signal list
The user must be able to search for signals in the signal list panel by typing a text.

### HLFR-00034 Approximate search
The search (HLFR-00033) must find a signal even when the typed text is not exactly the signal's name.

Note: For example, typing part of the name, typing it in a different case, leaving out separators such as `_`, or making a small spelling mistake must still find the signal.

## Plot panel

### HLFR-00014 Plot tabs
The plot panel must organize the plots in tabs.

### HLFR-00015 Add a tab
The user must be able to add a new tab to the plot panel.

### HLFR-00016 Delete a tab
The user must be able to delete a tab from the plot panel.

### HLFR-00017 Rename a tab
The user must be able to rename a tab.

### HLFR-00018 Plots per tab
Each tab must hold a maximum of 5 plots.

Note: A plot is an area of the tab in which signal curves are drawn.

### HLFR-00019 Delete a plot
The user must be able to delete a plot from a tab.

### HLFR-00020 Curve colors
The app must draw each signal curve in a plot in a different color.

Note: Colors only need to be different within one plot. Curves in different plots may share a color.

### HLFR-00021 Plot legend
Each plot must have a legend that identifies its curves.

### HLFR-00022 Remove a signal from a plot
The user must be able to remove a signal's curve from a plot.

### HLFR-00023 Curve width
The user must be able to set the width of a curve to one of 5 preset widths, numbered 1 to 5, where a higher number is a wider curve.

### HLFR-00024 Read curve values
The user must be able to read the x-axis and y-axis values of a point on a curve.

### HLFR-00025 Pin curve values
The user must be able to keep the values of a chosen point on a curve displayed in the plot.

### HLFR-00027 Zoom a plot
The user must be able to zoom in and zoom out of a plot along the x-axis.

### HLFR-00028 Place a vertical marker
The user must be able to place a vertical marker on a plot, at a chosen point of the x-axis.

Note: A **vertical marker** is a vertical line drawn across the plot at one time value, with a name label at its top.

### HLFR-00029 Move a vertical marker
The user must be able to move a vertical marker along the x-axis of its plot.

### HLFR-00030 Rename a vertical marker
The user must be able to rename a vertical marker.

### HLFR-00031 Delete a vertical marker
The user must be able to delete a vertical marker from a plot.

### HLFR-00035 Reset the zoom
The user must be able to return the plots to the whole time range of the file in one action.

### HLFR-00036 Pan a plot
The user must be able to move the time range shown in a zoomed plot along the x-axis.

### HLFR-00037 Plot grid
The user must be able to show and hide a grid on the plots.

### HLFR-00038 Export the plots to PDF
The user must be able to save the plots of all tabs to a PDF file.

### HLFR-00039 Copy the plots as an image
The user must be able to copy the plots of the current tab to the clipboard as an image that can be pasted in other applications.

### HLFR-00041 Move a pinned tip
The user must be able to move a pinned tip to another place in the plot, while it keeps showing the values of the same point.

### HLFR-00043 Measure a time difference
The user must be able to measure the time difference between two points on the curves of a plot.

Note: The measurement is shown in the plot by a **Delta X marker**.

### HLFR-00044 Measure a value difference
The user must be able to measure the y-axis value difference between two points on the curves of a plot.

Note: The measurement is shown in the plot by a **Delta Y marker**. Delta X and Delta Y markers are both called **delta markers**.
