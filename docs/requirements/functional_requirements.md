# Functional Requirements

Prefixes: `HLFR` (high-level) and `LLFR` (low-level). Format rules: see [README.md](README.md).
Rules for creating and changing functional requirements: PCR-00028 to PCR-00031 in [process_of_collaboration.md](process_of_collaboration.md).

The file has one section for HLFRs and one for LLFRs. Inside each, the requirements are grouped by part of the interface: General, Top panel, Signal list panel and Plot panel.

## High-level functional requirements

### General

#### HLFR-00001 Interface layout
The app interface must be divided into three panels: a top panel, a plot panel and a signal list panel.

Note: The **top panel** holds the controls for opening a file and for the plot tools. The **plot panel** shows the plots where signal curves are drawn, organized in tabs. The **signal list panel** shows the signals of the opened file, from which the user picks what to plot.

#### HLFR-00002 Error notification
When an error occurs, the app must notify the user with an error box that describes the error.

Note: The error box shown when a file cannot be opened is called the **File Open Error box**.

#### HLFR-00003 Active button indication
The interface must show which buttons are active.

Note: This applies to every button, including the button that opens a file.

### Top panel

#### HLFR-00004 Open a file
The user must be able to open a time series file from the top panel.

#### HLFR-00005 Supported file formats
The app must open files in these formats: CSV (`.csv`), Excel (`.xlsx`) and MATLAB (`.mat`).

Note: More formats may be added in later versions.

#### HLFR-00006 Time signal name
The app must identify the time signal as the signal named `Time`.

#### HLFR-00007 Time unit
The app must treat the values of the time signal as seconds.

Note: Files are assumed to always store time in seconds.

#### HLFR-00008 Minimum file content
The app must open a file only if it contains a time signal (HLFR-00006) and at least one other signal.

#### HLFR-00009 Equal sample count
The app must open a file only if all its signals have the same number of samples.

#### HLFR-00010 Replace file confirmation
If the selected file can be opened and another file is already open, the app must ask the user whether to proceed, stating that proceeding will close the current file.

### Signal list panel

#### HLFR-00011 Signal list
The signal list panel must show the names of the signals contained in the opened file.

Note: The updated signal list is the confirmation that the file was opened successfully.

#### HLFR-00012 Plot a signal in a new plot
The user must be able to plot a signal from the signal list in a new plot.

#### HLFR-00013 Add a signal to an existing plot
The user must be able to add a signal from the signal list to an existing plot.

### Plot panel

#### HLFR-00014 Plot tabs
The plot panel must organize the plots in tabs.

#### HLFR-00015 Add a tab
The user must be able to add a new tab to the plot panel.

#### HLFR-00016 Delete a tab
The user must be able to delete a tab from the plot panel.

#### HLFR-00017 Rename a tab
The user must be able to rename a tab.

#### HLFR-00018 Plots per tab
Each tab must hold a maximum of 5 plots.

Note: A plot is an area of the tab in which signal curves are drawn.

#### HLFR-00019 Delete a plot
The user must be able to delete a plot from a tab.

#### HLFR-00020 Curve colors
The app must draw each signal curve in a plot in a different color.

Note: Colors only need to be different within one plot. Curves in different plots may share a color.

#### HLFR-00021 Plot legend
Each plot must have a legend that identifies its curves.

#### HLFR-00022 Remove a signal from a plot
The user must be able to remove a signal's curve from a plot.

#### HLFR-00023 Curve width
The user must be able to set the width of a curve to one of 5 preset widths, numbered 1 to 5, where a higher number is a wider curve.

#### HLFR-00024 Read curve values
The user must be able to read the x-axis and y-axis values of a point on a curve.

#### HLFR-00025 Pin curve values
The user must be able to keep the values of a chosen point on a curve displayed in the plot.

## Low-level functional requirements

### General

#### LLFR-00001 Active button color
When the user clicks a button, the app must change the button's color to show that it is active.

*Parent: HLFR-00003*

#### LLFR-00002 Deactivate by second click
When the user clicks an active button again, the app must return the button to its normal color.

*Parent: HLFR-00003*

#### LLFR-00003 Deactivate when finished
When the function started by a button has finished, the app must return the button to its normal color.

*Parent: HLFR-00003*

#### LLFR-00058 Panel positions
The top panel must be placed above the other two panels, and the signal list panel must be placed to the right of the plot panel.

*Parent: HLFR-00001*

### Top panel

#### LLFR-00004 Open file button
The top panel must contain a button called "Open file".

*Parent: HLFR-00004*

#### LLFR-00005 File selection dialog
When the user clicks the open file button (LLFR-00004), the app must show a file selection dialog.

*Parent: HLFR-00004*

#### LLFR-00006 Open the selected file
When the user selects a file in the file selection dialog (LLFR-00005), the app must try to open that file.

*Parent: HLFR-00004*

#### LLFR-00007 Cancel file selection
If the user cancels the file selection dialog (LLFR-00005), the app must keep the currently opened file and its signal list unchanged.

*Parent: HLFR-00004*

#### LLFR-00008 Unreadable file
If the file cannot be read or parsed (for example, it is corrupt or its content does not match its format), the app must show the File Open Error box saying that the file could not be read.

*Parent: HLFR-00004, HLFR-00002*

#### LLFR-00009 File access error
If the file does not exist or the app has no permission to read it, the app must show the File Open Error box saying that the file could not be accessed.

*Parent: HLFR-00004, HLFR-00002*

#### LLFR-00010 State after a failed open
When opening a file fails, the app must keep the previously opened file and its signal list unchanged.

*Parent: HLFR-00004*

#### LLFR-00011 Unsupported file format
If the user selects a file whose format is not listed in HLFR-00005, the app must show the File Open Error box saying that the file format is not supported.

*Parent: HLFR-00005, HLFR-00002*

#### LLFR-00012 Failed content check message
If the file fails the check in HLFR-00008 or HLFR-00009, the app must show the File Open Error box saying that the file cannot be opened and which check failed.

*Parent: HLFR-00008, HLFR-00009, HLFR-00002*

#### LLFR-00013 Replace file accepted
If the user proceeds in the confirmation of HLFR-00010, the app must close the current file and open the selected one.

*Parent: HLFR-00010*

#### LLFR-00014 Replace file declined
If the user does not proceed in the confirmation of HLFR-00010, the app must keep the current file open.

*Parent: HLFR-00010*

#### LLFR-00015 Close plots on replace
When the app replaces the current file (LLFR-00013), it must close all tabs and plots of the previous file.

*Parent: HLFR-00010*

#### LLFR-00016 Initial state on replace
After closing the previous file's tabs and plots (LLFR-00015), the plot panel must contain one tab with no plots.

*Parent: HLFR-00010, HLFR-00014*

#### LLFR-00017 Signal list on replace
When the app replaces the current file (LLFR-00013), the signal list panel must show only the signal names of the new file.

*Parent: HLFR-00010, HLFR-00011*

#### LLFR-00018 Tip button
The top panel must contain a button called "Tip".

*Parent: HLFR-00024*

#### LLFR-00053 Case-sensitive time signal name
The app must match the time signal name `Time` (HLFR-00006) case-sensitively, so that a signal named `time` or `TIME` is not the time signal.

*Parent: HLFR-00006*

#### LLFR-00059 CSV and Excel layout
In CSV and Excel files, the app must read each column as one signal and each row below the first as one sample, and must take the signal names from the first row.

*Parent: HLFR-00005*

#### LLFR-00060 Excel first sheet
In Excel files, the app must read only the first sheet and ignore any other sheets.

*Parent: HLFR-00005*

#### LLFR-00061 CSV style detection
The app must detect automatically whether a CSV file uses `,` as the separator and `.` as the decimal mark, or `;` as the separator and `,` as the decimal mark, and read the file in the detected style.

*Parent: HLFR-00005*

#### LLFR-00062 MAT file signals
In MAT files, the app must read each top-level variable that holds a one-dimensional numeric array (1×N or N×1) as one signal, named after the variable.

*Parent: HLFR-00005*

#### LLFR-00063 Other MAT variables
In MAT files, the app must ignore top-level variables that do not hold a one-dimensional numeric array, and must apply the checks of HLFR-00008 and HLFR-00009 only to the signals it read.

*Parent: HLFR-00005, HLFR-00008, HLFR-00009*

#### LLFR-00064 MAT v7.3 files
If a MAT file was saved in the MATLAB v7.3 format, the app must show the File Open Error box saying that the file could not be read.

Note: Support for v7.3 files needs an extra library and may be added later (COR-00011).

*Parent: HLFR-00005, HLFR-00002*

#### LLFR-00065 Missing or non-numeric values
If a sample of any signal in a CSV or Excel file is empty or is not a number, the app must show the File Open Error box saying that the file could not be read.

*Parent: HLFR-00004, HLFR-00002*

### Signal list panel

#### LLFR-00019 Double-click creates a plot
When the user double-clicks a signal name in the signal list panel, the app must create a new plot in the current tab.

*Parent: HLFR-00012*

#### LLFR-00020 Double-click draws the signal
When the app creates a plot by double-click (LLFR-00019), it must draw the double-clicked signal in that plot.

*Parent: HLFR-00012*

#### LLFR-00021 Drag and drop on a plot
When the user drags a signal name and drops it on a plot, the app must draw the signal in that plot.

*Parent: HLFR-00013*

#### LLFR-00022 Drop outside a plot creates nothing
If the user drops a signal name anywhere other than on a plot, the app must not create a plot.

*Parent: HLFR-00013*

#### LLFR-00023 Drop outside a plot shows nothing
If the user drops a signal name anywhere other than on a plot, the app must not show any message.

*Parent: HLFR-00013*

#### LLFR-00054 Time signal in the signal list
The signal list panel must include the time signal (HLFR-00006) among the signal names it shows.

*Parent: HLFR-00011, HLFR-00006*

#### LLFR-00055 Plotting the time signal
The app must let the user plot the time signal (HLFR-00006) in the same ways as any other signal.

*Parent: HLFR-00012, HLFR-00013*

#### LLFR-00056 Drop a signal already in the plot
If the user drops a signal name on a plot that already shows that signal, the app must not draw the signal again.

*Parent: HLFR-00013*

#### LLFR-00057 No message on duplicate drop
If the user drops a signal name on a plot that already shows that signal, the app must not show any message.

*Parent: HLFR-00013*

### Plot panel

#### LLFR-00024 Initial tab
When the app starts, the plot panel must contain one tab.

*Parent: HLFR-00014*

#### LLFR-00025 Add tab button
The plot panel must show a "+" button directly beside the last tab.

*Parent: HLFR-00015*

#### LLFR-00026 Add tab button action
When the user clicks the "+" button (LLFR-00025), the app must add a new tab.

*Parent: HLFR-00015*

#### LLFR-00027 Tab menu delete option
When the user right-clicks a tab, the app must show a menu with a "Delete" option.

*Parent: HLFR-00016*

#### LLFR-00028 Delete tab action
When the user chooses "Delete" in the tab menu (LLFR-00027), the app must remove that tab.

*Parent: HLFR-00016*

#### LLFR-00029 Tab menu rename option
When the user right-clicks a tab, the app must show a menu with a "Rename" option.

*Parent: HLFR-00017*

#### LLFR-00030 Rename tab action
When the user chooses "Rename" in the tab menu (LLFR-00029), the app must let the user type a new name for that tab.

*Parent: HLFR-00017*

#### LLFR-00031 Full tab blocks new plots
If the user tries to create a new plot in a tab that already holds the maximum number of plots (HLFR-00018), the app must not create the plot.

*Parent: HLFR-00018*

#### LLFR-00032 Full tab notification
When the app does not create a plot because the tab is full (LLFR-00031), it must show the Full Tab Notification box, telling the user to add a new tab or delete a plot.

Note: The Full Tab Notification box is an information message, not an error box (HLFR-00002).

*Parent: HLFR-00018*

#### LLFR-00033 Predefined curve colors
The first 8 signals drawn in a plot must use a predefined palette of 8 colors that are easy to tell apart.

*Parent: HLFR-00020*

#### LLFR-00034 Random curve colors
From the 9th signal drawn in a plot onward, the app must give each new curve a randomly generated color that is different from the colors already used in that plot.

*Parent: HLFR-00020*

#### LLFR-00035 Legend position
The legend must be placed directly above its plot.

*Parent: HLFR-00021*

#### LLFR-00036 Legend names
The legend must show the names of the signals drawn in its plot.

*Parent: HLFR-00021*

#### LLFR-00037 Legend colors
Each signal name in the legend must be shown in the same color as its curve.

*Parent: HLFR-00021*

#### LLFR-00038 Curve menu delete option
When the user right-clicks a curve in a plot, the app must show a menu with a "Delete signal" option.

*Parent: HLFR-00022*

#### LLFR-00039 Delete signal action
When the user chooses "Delete signal" in the curve menu (LLFR-00038), the app must remove that curve from the plot.

*Parent: HLFR-00022*

#### LLFR-00040 Curve menu width option
When the user right-clicks a curve in a plot, the app must show a menu with a "Width" option that lists the preset widths 1 to 5.

*Parent: HLFR-00023*

#### LLFR-00041 Set width action
When the user chooses a preset width in the "Width" option of the curve menu (LLFR-00040), the app must draw that curve with the chosen width.

*Parent: HLFR-00023*

#### LLFR-00042 Hover tip
While the Tip button (LLFR-00018) is active and the user hovers over a curve, the app must show a tip with the x-axis and y-axis values of the hovered point.

*Parent: HLFR-00024*

#### LLFR-00043 Tip x value
The tip must show the x-axis value in seconds.

*Parent: HLFR-00024, HLFR-00007*

#### LLFR-00044 Tip y value
The tip must show the y-axis value as stored in the file, without a unit.

*Parent: HLFR-00024*

#### LLFR-00045 Pin a tip
If the user left-clicks a curve while the hover tip (LLFR-00042) is shown, the app must fix the tip at that point in the plot.

*Parent: HLFR-00025*

#### LLFR-00046 Pinned tip menu
When the user right-clicks a pinned tip, the app must show a menu with a "Delete" option.

*Parent: HLFR-00025*

#### LLFR-00047 Remove a pinned tip
When the user chooses "Delete" in the pinned tip menu (LLFR-00046), the app must remove the pinned tip from the plot.

*Parent: HLFR-00025*

#### LLFR-00048 Plot menu delete option
When the user right-clicks an empty area of a plot (not on a curve or a pinned tip), the app must show a menu with a "Delete plot" option.

*Parent: HLFR-00019*

#### LLFR-00049 Delete plot action
When the user chooses "Delete plot" in the plot menu (LLFR-00048), the app must remove that plot and all its curves from the tab.

*Parent: HLFR-00019*

#### LLFR-00050 Space after deleting a plot
After a plot is deleted, the app must resize the remaining plots in the tab to fill the free space.

*Parent: HLFR-00019*

#### LLFR-00051 Remove empty plot
When the last curve of a plot is removed (LLFR-00039), the app must delete that plot from the tab, as in LLFR-00049 and LLFR-00050.

*Parent: HLFR-00022, HLFR-00019*

#### LLFR-00052 Default curve width
When the app draws a new curve, it must use preset width 1.

*Parent: HLFR-00023*

#### LLFR-00066 Keep at least one tab
When the plot panel has only one tab, the app must show the "Delete" option of the tab menu (LLFR-00027) as disabled, so that the last tab cannot be deleted.

*Parent: HLFR-00016, HLFR-00014*

#### LLFR-00067 Empty tab name
If the user enters a tab name that is empty or made only of spaces (LLFR-00030), the app must keep the tab's previous name and must not show any message.

*Parent: HLFR-00017*

#### LLFR-00068 Time on the x-axis
Every plot must use the time signal (HLFR-00006) as its x-axis.

*Parent: HLFR-00012, HLFR-00013, HLFR-00007*

#### LLFR-00069 Vertical stacking of plots
The plots in a tab must be stacked vertically, one below the other.

*Parent: HLFR-00014, HLFR-00018*

#### LLFR-00070 Shared time axis
The plots in a tab must share the same x-axis range, so that a change to the time range of one plot applies to all plots in that tab.

*Parent: HLFR-00014*
