# High-Level Functional Requirements

Prefix: `HLFR`. Format rules: see [README.md](README.md).
Rules for creating and changing functional requirements: PCR-00028 to PCR-00031 in [process_of_collaboration.md](process_of_collaboration.md).
The low-level requirements that refine these are in [low_level_functional_requirements.md](low_level_functional_requirements.md).

The requirements are grouped by part of the interface: General, Top panel, Signal list panel and Plot panel.

## General

### HLFR-00001 Interface layout
The app interface must be divided into three panels: a top panel, a plot panel and a signal list panel.

Note: The **top panel** holds the controls for opening a file and for the plot tools. The **plot panel** shows the plots where signal curves are drawn, organized in tabs. The **signal list panel** shows the signals of the open data files, from which the user picks what to plot.

### HLFR-00002 Error notification
When an error occurs, the app must notify the user with an error box that describes the error.

Note: The error box shown when a file cannot be opened is called the **File Open Error box**.

### HLFR-00003 Active button indication
The interface must show which buttons are active.

Note: This applies to every button, including the button that opens a file.

### HLFR-00026 Resize the panels
The user must be able to change the widths of the plot panel and the signal list panel.

### HLFR-00040 Undo
The user must be able to undo their most recent actions on the tabs, plots, curves, data tips, flags, delta markers, areas, text notes and arrows.

### HLFR-00048 Redo
The user must be able to redo the actions they have undone (HLFR-00040).

### HLFR-00045 App icon
The app must have its own custom icon, shown wherever the operating system shows the app.

### HLFR-00046 Splash screen
While the app is starting, it must show the user a splash screen.

### HLFR-00047 Opening time
The app must open quickly, so that the user waits as little as possible before it is ready to use.

### HLFR-00091 Dialog opening time
The windows in which the user chooses a file to open or to save must appear quickly after the user asks for them.


## Top panel

### HLFR-00004 Open a file
The user must be able to open a time series file from the top panel.

### HLFR-00122 Open several files at once
The user must be able to select several files at once in the dialog of the Open file button and open them all with that one choice.

### HLFR-00005 Supported file formats
The app must open files in these formats: CSV (`.csv`), Excel (`.xlsx`), MATLAB (`.mat`) and HDF5 (`.h5`, `.hdf5`).

Note: More formats may be added in later versions.

### HLFR-00006 Time signal name
The app must identify the time signal of each data file as the signal of that file whose name in the file is `Time`, ignoring the difference between uppercase and lowercase letters, or, when no signal of the file has that name, as the signal the user chooses (HLFR-00070).

Note: The time signal of a file gives the times of the curves of that file in the time plots (HLFR-00116).

### HLFR-00007 Time unit
The app must treat the values of the time signal as seconds.

Note: Files are assumed to always store time in seconds.

### HLFR-00008 Minimum file content
The app must open a file only if it contains at least two signals, one of which is the time signal (HLFR-00006).

### HLFR-00009 Equal sample count
The app must open a file only if all its signals have the same number of samples.

### HLFR-00113 Several data files open
The user must be able to have up to 10 data files open at the same time.

Note: Each file opened with the Open file button is a **data file** (HLFR-00049).

### HLFR-00114 File numbers
The app must give each data file a number, in the order the files are opened, starting at 1 when the app starts and never giving again the number of a closed file while the app runs.

Note: For example, after file 2 of three open files is closed, file 3 keeps the number 3, and the next file opened is file 4.

### HLFR-00010 DELETED
DELETED

### HLFR-00117 Opening adds a file
When the user opens a file while other data files are open, the app must add it to the open data files, with no question, keeping the data files already open.

Note: Opening a file never asks to close the data files already open (LLFR-00918).

### HLFR-00101 Failed open keeps the open files
If a selected file cannot be opened, the app must keep the data files already open unchanged.

### HLFR-00032 One plot tool at a time
The app must allow only one plot tool to be active at a time.

Note: The **plot tools** are the Data tip, Zoom, Pan, Flag, Delta X, Delta Y, Area, Text and Arrow functions. Each one is started from its own button in the top panel.

### HLFR-00042 Button icons
Each button in the top panel must show an icon that illustrates its function.

Note: The small box with a button's name that appears while the mouse pointer is over the button is called a **button tip**. It is not a data tip (HLFR-00024).

### HLFR-00049 Save a layout
The user must be able to save the current layout of the plots to a layout file from the top panel.

Note: The **layout** is what the plot panel shows and how: the tabs, their plots, the curves in each plot, the time range, the grid, the flags, the areas, the delta markers and the pinned data tips. A **layout file** is a file that holds a layout. Each file with time series that the user opens with the Open file button is called a **data file**; several can be open at once (HLFR-00113). The layout is saved with the **Save layout** button and loaded with the **Load layout** button.

### HLFR-00050 Load a layout
The user must be able to load a layout file from the top panel and rebuild its layout with the signals of the open data files.

### HLFR-00051 Layout file format
The layout file must be a text file that the user can read and edit by hand in a text editor.

### HLFR-00052 Layout load report
After loading a layout file, the app must tell the user which parts of the layout it could not rebuild and why.

### HLFR-00056 Synthetic signals in the layout
The layout file must hold what the app needs to create again the synthetic signals (HLFR-00053) when the layout file is loaded, except the FFT signals, which are not saved in the layout file.

### HLFR-00070 Choose the time signal
When the user opens a file in which no signal is named `Time` (HLFR-00006), the app must ask the user to choose the signal that goes on the x-axis, in a window with the list of the signals and a search box.

Note: The window works like the second signal window of the Product with signal operation.

### HLFR-00072 Time signal fixed after opening
The user must not be able to change the time signal after its file is open.

### HLFR-00077 Button groups
The buttons of the top panel must be organized in groups of related buttons.

Note: The groups are: Open file, Save layout and Load layout; the plot tools (HLFR-00032); Reset zoom and Grid; Export, Copy and Save signals; Undo and Redo; Report a bug (HLFR-00078).

### HLFR-00102 Joined buttons in a group
The buttons of a group (HLFR-00077) must look like one joined block, with no space between them.

### HLFR-00103 Space between button groups
There must be a space between one button group (HLFR-00077) and the next.

### HLFR-00078 Report a bug
The user must be able to open, from the top panel, the page that creates a new issue in the project's GitHub repository, in their web browser.

Note: The page is opened with the **Report a bug** button.

### HLFR-00080 Author credit
The top panel must show the text "Designed by materodr" in its upper-right corner.

### HLFR-00090 Save the signals to a data file
The user must be able to save, from the top panel, the signals of the signal list, including the synthetic signals, to a new file in one of the formats of HLFR-00005, which the app can open again as a data file, except as in HLFR-00120.

Note: FFT signals are not saved, because their samples are frequencies, not times (HLFR-00009). The file is written with the **Save signals** button.

### HLFR-00120 Same time signals to save several files
The app must save the signals of the open data files to one file only when all the open data files have exactly the same time signal.

### HLFR-00121 Saved names without the file prefix
The app must save each signal under its name without the prefix of HLFR-00115, also inside the names of synthetic signals.

Note: For example, `file1_Speed` is saved as `Speed`, and `file1_int_Speed` as `int_Speed`.

## Signal list panel

### HLFR-00011 Signal list
The signal list panel must show the names of the signals contained in the open data files.

Note: The new file name row and its signals are the confirmation that the file was opened successfully.

### HLFR-00115 Signal name prefix
The app must name each signal of a data file with `file`, the file's number (HLFR-00114), an underscore and the signal's name in the file, for example `file1_Speed`.

Note: This prefixed name is the signal's name everywhere in the app, also while only one data file is open, except in the time signal window (HLFR-00070) and in the files written by the Save signals button (HLFR-00121).

### HLFR-00012 Plot a signal in a new plot
The user must be able to plot a signal from the signal list in a new plot.

### HLFR-00013 Add a signal to an existing plot
The user must be able to add a signal from the signal list to an existing plot.

### HLFR-00033 Search the signal list
The user must be able to search for signals in the signal list panel by typing a text.

### HLFR-00034 Approximate search
The search (HLFR-00033) must also find the signals whose names are close to the typed text.

Note: For example, typing part of the name, typing it in a different case, leaving out separators such as `_`, or making a small spelling mistake still finds the signal.

### HLFR-00053 Synthetic signals
The user must be able to create, from a signal in the signal list, including a synthetic signal, a new signal computed from it.

Note: Such a signal is called a **synthetic signal**. The operations that create one are Integral, Derivative, Low-pass filter, High-pass filter, Moving average, Max, Min, Greater than, Less than, Greater than or equal, Less than or equal, Add constant, Subtract constant, Multiply by constant, Divide by constant, Absolute value, Product with signal and FFT. Product with signal multiplies two signals sample by sample; the Comparison operations and the other Arithmetic operations, except Absolute value, use a constant number. An FFT signal is a synthetic signal created by the FFT operation.

### HLFR-00054 Synthetic signal name
Except for the product of two signals (HLFR-00104), the app must name each synthetic signal with the prefix of its data file (HLFR-00115), the abbreviation of its operation shown in the menu, an underscore, the value of its parameter when it has one, an underscore and the name, without its prefix, of the signal it was computed from. The parameter of an FFT signal is the time range it was computed from (HLFR-00057).

Note: For example, `file1_int_Speed`, and `file1_int_lpf_2Hz_order2_Speed` for the Integral of a Low-pass filter of `file1_Speed`.

### HLFR-00104 Product signal name
For the product of two signals, the name of the synthetic signal must be the name of the first signal with its prefix (HLFR-00115), the abbreviation of the operation and the name of the second signal, separated by underscores, where the name of the second signal keeps its own prefix only when it belongs to another data file.

Note: For example, `file1_Speed_prod_Torque` for two signals of file 1, and `file1_Speed_prod_file2_Torque` when `Torque` belongs to file 2.

### HLFR-00055 Synthetic signals in memory
The app must keep synthetic signals only in its memory.

### HLFR-00105 Synthetic signals not in the data files
The app must not add synthetic signals to any data file.

### HLFR-00057 FFT time range
The app must compute an FFT signal only from the samples within the time range shown in the plots when the FFT signal is created.

### HLFR-00059 Delete a synthetic signal
The user must be able to delete a synthetic signal.

### HLFR-00060 Rename a synthetic signal
The user must be able to rename a synthetic signal.

### HLFR-00061 Copy a signal name
The user must be able to copy the name of a signal in the signal list to the clipboard.

### HLFR-00062 Copy the equation of a synthetic signal
The user must be able to copy to the clipboard the equation of a synthetic signal.

Note: The **equation** of a synthetic signal is the text that the layout file uses to create it again (HLFR-00056), including every synthetic signal it is computed from.

### HLFR-00063 Select several signals
The user must be able to select several signals in the signal list at once.

### HLFR-00064 Plot several signals in a new plot
The user must be able to plot the selected signals together, as curves of one new plot, by pressing the Enter key.

### HLFR-00065 Add several signals to an existing plot
The user must be able to add all the selected signals to an existing plot at once, by dragging them to it.

### HLFR-00071 Time signal shown in green
The signal list panel must show the name of the time signal of each data file in green, whether the app found it by its name or the user chose it.

### HLFR-00079 Names of the open files
The signal list panel must show the name of each open data file, with its file number (HLFR-00114), in a row above the signals of that file.

### HLFR-00118 Close a file
The user must be able to close one open data file from the signal list panel.

Note: Closing a file removes its signals, the synthetic signals computed from its signals and their curves.

### HLFR-00119 Close all files
The user must be able to close all the open data files in one action from the signal list panel.

### HLFR-00095 Search box aligned with the plots
The bottom of the search box must be aligned with the bottom of the last plot.

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

Note: The box that shows these values in the plot is called a **data tip**. A data tip shown while the mouse pointer hovers over a curve is a **hover data tip**; a data tip fixed at a point by a click is a **pinned data tip** (HLFR-00025).

### HLFR-00025 Pin curve values
The user must be able to keep the values of a chosen point on a curve displayed in the plot.

### HLFR-00027 Zoom a plot
The user must be able to zoom in and zoom out of a plot along the x-axis.

### HLFR-00028 Place a flag
The user must be able to place a flag at a chosen point of the x-axis, shown on every plot.

Note: A **flag** is a vertical line drawn across the plot at one time value, with a name label at its top.

### HLFR-00029 Move a flag
The user must be able to move a flag along the x-axis of its plot.

### HLFR-00030 Rename a flag
The user must be able to rename a flag.

### HLFR-00031 Delete a flag
The user must be able to delete a flag from a plot.

### HLFR-00035 Reset the zoom
The user must be able to return the plots, in one action, to the whole time range of the open data files, from the earliest first time sample to the latest last time sample of all of them.

### HLFR-00036 Pan a plot
The user must be able to move the time range shown in a zoomed plot along the x-axis.

### HLFR-00037 Plot grid
The user must be able to show and hide a grid on the plots.

### HLFR-00038 Export the plots to PDF
The user must be able to save the plots of all tabs to a PDF file.

### HLFR-00039 Copy the plots as an image
The user must be able to copy the plots of the current tab to the clipboard as an image that can be pasted in other applications.

### HLFR-00041 Move a pinned data tip
The user must be able to move a pinned data tip to another place in the plot, while it keeps showing the values of the same point.

### HLFR-00043 Measure a time difference
The user must be able to measure the time difference between two points on the curves of a plot.

Note: The measurement is shown in the plot by a **Delta X marker**.

### HLFR-00044 Measure a value difference
The user must be able to measure the y-axis value difference between two points on the curves of a plot.

Note: The measurement is shown in the plot by a **Delta Y marker**. Delta X and Delta Y markers are both called **delta markers**.

### HLFR-00058 Frequency plots
The app must draw FFT signals in plots that have frequency on their x-axis.

Note: Such a plot is called a **frequency plot**. A plot that has time on its x-axis is called a **time plot**.

### HLFR-00116 Signals of several files in one plot
The user must be able to draw signals of different data files in the same time plot, each curve against the time signal of its own file.

### HLFR-00066 Mark a time range with an area
The user must be able to mark a time range with an area, shown on every time plot.

Note: An **area** is a shaded vertical band across the plot, between two time values, with a name label at its top. It is started from the **Area** button in the top panel.

### HLFR-00067 Move an area
The user must be able to move an area along the x-axis.

### HLFR-00106 Resize an area
The user must be able to change the start and end times of an area.

### HLFR-00068 Rename an area
The user must be able to rename an area.

### HLFR-00069 Delete an area
The user must be able to delete an area.

### HLFR-00073 Write text on a plot
The user must be able to write any text at any place in a plot.

Note: Such a text is called a **text note**. It is started from the **Text** button in the top panel.

### HLFR-00074 Move a text note
The user must be able to move a text note to another place in the plot.

### HLFR-00075 Edit a text note
The user must be able to change the text of a text note.

### HLFR-00076 Delete a text note
The user must be able to delete a text note.

### HLFR-00081 Draw an arrow on a plot
The user must be able to draw an arrow at any place in a plot, pointing in any direction.

Note: An **arrow** is a straight line with an arrowhead at one of its ends. It is started from the **Arrow** button in the top panel.

### HLFR-00082 Move an arrow
The user must be able to move an arrow to another place in the plot, keeping its length and direction.

### HLFR-00083 Rotate and stretch an arrow
The user must be able to turn an arrow around one of its ends and to make it longer or shorter.

### HLFR-00084 Delete an arrow
The user must be able to delete an arrow.

### HLFR-00085 Edit the objects with no tool active
When no plot tool is active, the user must be able to move flags, areas, pinned data tips, text notes, arrows and the points of delta markers, to resize areas and to rotate and stretch arrows, by dragging them with the mouse.

### HLFR-00086 Text note size
The user must be able to change the size of the text of a text note.

### HLFR-00087 Text note colors
The user must be able to change the border color and the text color of a text note.

### HLFR-00088 Pick any color
The user must be able to give any color to an arrow, a flag, the border and the text of a text note, an area and a delta marker, choosing it in one color picker that is the same for all of them.

### HLFR-00089 Flag color
The user must be able to change the color of a flag.

### HLFR-00092 Delta marker color
The user must be able to change the color of a delta marker.

### HLFR-00093 Delete all objects of one kind
The user must be able to delete in one action all the pinned data tips of a plot or of all plots, all the delta markers of a plot or of all plots, all the flags, or all the areas.

### HLFR-00094 Rename a label by double-click
The user must be able to rename a tab, a flag, an area, a delta marker and an arrow by double-clicking its label.

Note: A text note is edited by a double-click in the same way (HLFR-00075).

### HLFR-00107 Double-click changes only the name
The double-click of HLFR-00094 must change only the name, never a time or another value linked to the plotted curves.

Note: The time of a flag, for example, changes only by moving the flag.

### HLFR-00096 Object name in the plot menus
The menu that appears when the user right-clicks in a plot must show, at its top, the name of the object it acts on.

### HLFR-00108 Menu name look
The name at the top of a plot menu (HLFR-00096) must look different from the options.

### HLFR-00109 Menu name not clickable
The name at the top of a plot menu (HLFR-00096) must not be an option that can be clicked.

### HLFR-00097 Name of a delta marker
Each delta marker must show a label with its name.

### HLFR-00110 Rename a delta marker
The user must be able to rename a delta marker.

### HLFR-00098 No delta marker of value zero
The app must not create a delta marker whose value is zero.

### HLFR-00099 Move the points of a delta marker
The user must be able to move each of the two points of a delta marker after it is created, by dragging it with the mouse.

### HLFR-00100 Name of an arrow
Each arrow must show a label with its name, parallel to its straight line.

### HLFR-00111 Rename an arrow
The user must be able to rename an arrow.

### HLFR-00112 Arrow label follows the arrow
When the position or the angle of an arrow changes, its label (HLFR-00100) must change with it.
