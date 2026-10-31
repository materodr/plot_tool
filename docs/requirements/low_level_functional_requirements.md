# Low-Level Functional Requirements

Prefix: `LLFR`. Format rules: see [README.md](README.md).
Rules for creating and changing functional requirements: PCR-00028 to PCR-00031 in [process_of_collaboration.md](process_of_collaboration.md).
Each requirement names its parent in [high_level_functional_requirements.md](high_level_functional_requirements.md).

The requirements are grouped by part of the interface: General, Top panel, Signal list panel and Plot panel.

## General

### LLFR-00001 Active button color
When the user clicks a button, the app must change the button's color to show that it is active.

*Parent: HLFR-00003*

### LLFR-00002 Deactivate by second click
When the user clicks an active button again, the app must return the button to its normal color.

*Parent: HLFR-00003*

### LLFR-00003 Deactivate when finished
When the function started by a button has finished, the app must return the button to its normal color.

*Parent: HLFR-00003*

### LLFR-00058 Panel positions
The top panel must be placed above the other two panels, and the signal list panel must be placed to the right of the plot panel.

*Parent: HLFR-00001*

### LLFR-00071 Unexpected error box
If an unexpected error occurs while the app handles a user action, the app must show an error box titled "Error" that describes the error, and must keep running.

*Parent: HLFR-00002*

### LLFR-00072 Initial signal list width
When the app starts, the signal list panel must take 25% of the app window's width, and the plot panel must take the rest.

*Parent: HLFR-00001, HLFR-00026*

### LLFR-00073 Drag to resize the panels
The user must be able to drag the border between the plot panel and the signal list panel to change their widths.

*Parent: HLFR-00026*

## Top panel

### LLFR-00004 Open file button
The top panel must contain a button called "Open file".

*Parent: HLFR-00004*

### LLFR-00005 File selection dialog
When the user clicks the open file button (LLFR-00004), the app must show a file selection dialog.

*Parent: HLFR-00004*

### LLFR-00006 Open the selected file
When the user selects a file in the file selection dialog (LLFR-00005), the app must try to open that file.

*Parent: HLFR-00004*

### LLFR-00007 Cancel file selection
If the user cancels the file selection dialog (LLFR-00005), the app must keep the currently opened file and its signal list unchanged.

*Parent: HLFR-00004*

### LLFR-00008 Unreadable file
If the file cannot be read or parsed (for example, it is corrupt or its content does not match its format), the app must show the File Open Error box saying that the file could not be read.

*Parent: HLFR-00004, HLFR-00002*

### LLFR-00009 File access error
If the file does not exist or the app has no permission to read it, the app must show the File Open Error box saying that the file could not be accessed.

*Parent: HLFR-00004, HLFR-00002*

### LLFR-00010 State after a failed open
When opening a file fails, the app must keep the previously opened file and its signal list unchanged.

*Parent: HLFR-00004*

### LLFR-00011 Unsupported file format
If the user selects a file whose format is not listed in HLFR-00005, the app must show the File Open Error box saying that the file format is not supported.

*Parent: HLFR-00005, HLFR-00002*

### LLFR-00012 Failed content check message
If the file fails the check in HLFR-00008 or HLFR-00009, the app must show the File Open Error box saying that the file cannot be opened and which check failed.

*Parent: HLFR-00008, HLFR-00009, HLFR-00002*

### LLFR-00013 Replace file accepted
If the user proceeds in the confirmation of HLFR-00010, the app must close the current file and open the selected one.

*Parent: HLFR-00010*

### LLFR-00014 Replace file declined
If the user does not proceed in the confirmation of HLFR-00010, the app must keep the current file open.

*Parent: HLFR-00010*

### LLFR-00015 Close plots on replace
When the app replaces the current file (LLFR-00013), it must close all tabs and plots of the previous file.

*Parent: HLFR-00010*

### LLFR-00016 Initial state on replace
After closing the previous file's tabs and plots (LLFR-00015), the plot panel must contain one tab with no plots.

*Parent: HLFR-00010, HLFR-00014*

### LLFR-00017 Signal list on replace
When the app replaces the current file (LLFR-00013), the signal list panel must show only the signal names of the new file.

*Parent: HLFR-00010, HLFR-00011*

### LLFR-00018 Tip button
The top panel must contain a button called "Tip".

*Parent: HLFR-00024, HLFR-00032*

### LLFR-00053 Case-sensitive time signal name
The app must match the time signal name `Time` (HLFR-00006) case-sensitively, so that a signal named `time` or `TIME` is not the time signal.

*Parent: HLFR-00006*

### LLFR-00059 CSV and Excel layout
In CSV and Excel files, the app must read each column as one signal and each row below the first as one sample, and must take the signal names from the first row.

*Parent: HLFR-00005*

### LLFR-00060 Excel first sheet
In Excel files, the app must read only the first sheet and ignore any other sheets.

*Parent: HLFR-00005*

### LLFR-00061 CSV style detection
The app must detect automatically whether a CSV file uses `,` as the separator and `.` as the decimal mark, or `;` as the separator and `,` as the decimal mark, and read the file in the detected style.

*Parent: HLFR-00005*

### LLFR-00062 MAT file signals
In MAT files, the app must read each top-level variable that holds a one-dimensional numeric array (1×N or N×1) as one signal, named after the variable.

*Parent: HLFR-00005*

### LLFR-00063 Other MAT variables
In MAT files, the app must ignore top-level variables that do not hold a one-dimensional numeric array, and must apply the checks of HLFR-00008 and HLFR-00009 only to the signals it read.

*Parent: HLFR-00005, HLFR-00008, HLFR-00009*

### LLFR-00064 MAT v7.3 files
If a MAT file was saved in the MATLAB v7.3 format, the app must show the File Open Error box saying that the file could not be read.

Note: Support for v7.3 files needs an extra library and may be added later (COR-00011).

*Parent: HLFR-00005, HLFR-00002*

### LLFR-00065 Missing or non-numeric values
If a sample of any signal in a CSV or Excel file is empty or is not a number, the app must show the File Open Error box saying that the file could not be read.

*Parent: HLFR-00004, HLFR-00002*

### LLFR-00077 Zoom button
The top panel must contain a button called "Zoom".

*Parent: HLFR-00027, HLFR-00032*

### LLFR-00079 One active plot tool
When the user activates a plot tool button, the app must deactivate any other plot tool button that is active.

*Parent: HLFR-00032*

### LLFR-00080 Vertical marker button
The top panel must contain a button called "Vertical marker".

*Parent: HLFR-00028, HLFR-00032*

### LLFR-00109 Plot tools stay active
A plot tool button must stay active after its tool is used, until the user clicks the button again (LLFR-00002) or activates another plot tool (LLFR-00079).

Note: For a plot tool, the function of LLFR-00003 finishes only when the tool is deactivated, not after each zoom, pin or placed marker.

*Parent: HLFR-00032, HLFR-00003*

## Signal list panel

### LLFR-00019 Double-click creates a plot
When the user double-clicks a signal name in the signal list panel, the app must create a new plot in the current tab.

*Parent: HLFR-00012*

### LLFR-00020 Double-click draws the signal
When the app creates a plot by double-click (LLFR-00019), it must draw the double-clicked signal in that plot.

*Parent: HLFR-00012*

### LLFR-00021 Drag and drop on a plot
When the user drags a signal name and drops it on a plot, the app must draw the signal in that plot.

*Parent: HLFR-00013*

### LLFR-00022 Drop outside a plot creates nothing
If the user drops a signal name anywhere other than on a plot, the app must not create a plot.

*Parent: HLFR-00013*

### LLFR-00023 Drop outside a plot shows nothing
If the user drops a signal name anywhere other than on a plot, the app must not show any message.

*Parent: HLFR-00013*

### LLFR-00054 Time signal in the signal list
The signal list panel must include the time signal (HLFR-00006) among the signal names it shows.

*Parent: HLFR-00011, HLFR-00006*

### LLFR-00055 Plotting the time signal
The app must let the user plot the time signal (HLFR-00006) in the same ways as any other signal.

*Parent: HLFR-00012, HLFR-00013*

### LLFR-00056 Drop a signal already in the plot
If the user drops a signal name on a plot that already shows that signal, the app must not draw the signal again.

*Parent: HLFR-00013*

### LLFR-00057 No message on duplicate drop
If the user drops a signal name on a plot that already shows that signal, the app must not show any message.

*Parent: HLFR-00013*

### LLFR-00094 Search box
The signal list panel must contain a search box placed directly below the signal list.

*Parent: HLFR-00033*

### LLFR-00095 Filter while typing
Each time the text in the search box changes, the app must show in the signal list only the signals that match the text (LLFR-00098 to LLFR-00101 and LLFR-00105).

*Parent: HLFR-00033*

### LLFR-00096 Empty search
When the search box is empty or contains only spaces, the signal list must show all signals of the opened file.

*Parent: HLFR-00033*

### LLFR-00097 No matching signals
When no signal matches the text in the search box, the signal list must show no signals and must show the text "No matching signals".

*Parent: HLFR-00033*

### LLFR-00098 Case-insensitive search
The search must ignore the difference between uppercase and lowercase letters.

*Parent: HLFR-00034*

### LLFR-00099 Partial-name search
A search word (LLFR-00105) must match a signal when it appears anywhere in the signal's name.

*Parent: HLFR-00034*

### LLFR-00100 Separator-insensitive search
The search must ignore underscores (`_`), hyphens (`-`) and dots (`.`) in the typed text, and must ignore spaces, underscores, hyphens and dots in the signal names.

Note: For example, `enginespeed` finds `Engine_Speed`.

*Parent: HLFR-00034*

### LLFR-00101 Typo-tolerant search
When a search word (LLFR-00105), after LLFR-00098 and LLFR-00100 are applied, has 4 or more characters, it must also match a signal whose name contains a part that differs from the word by at most one wrong, missing or extra character for every full 4 characters of the word (1 for 4 to 7 characters, 2 for 8 to 11 characters, and so on).

Note: For example, `presure` finds `Pressure`, and `sine_2hz` finds `Sine_3Hz`.

*Parent: HLFR-00034*

### LLFR-00102 Order of search results
The app must list the matching signals, which are the signals whose name contains every search word, exactly or within the typo allowance of LLFR-00101 (LLFR-00105), in three groups in this order, keeping the file order within each group:
1. the signals that match every search word without LLFR-00101 and whose name, after LLFR-00098 and LLFR-00100 are applied, starts with the first search word;
2. the other signals that match every search word without LLFR-00101;
3. the signals that need LLFR-00101 for at least one search word.

*Parent: HLFR-00034*

### LLFR-00103 Plotting from search results
The user must be able to plot the signals shown in a filtered signal list in the same ways as in the full list (LLFR-00019, LLFR-00021).

*Parent: HLFR-00033, HLFR-00012, HLFR-00013*

### LLFR-00104 Search cleared on file replace
When the app replaces the current file (LLFR-00013), it must clear the search box.

*Parent: HLFR-00033, HLFR-00010*

### LLFR-00105 Multi-word search
The app must split the typed text into search words at each space, and a signal must match only when every search word matches its name (LLFR-00098 to LLFR-00101), in any order.

Note: For example, with the signals `mateus_soares_rodrigues 2026` and `mateus_soares_rodrigues 2025`, typing `mate so 25` finds only `mateus_soares_rodrigues 2025`.

*Parent: HLFR-00034*

## Plot panel

### LLFR-00024 Initial tab
When the app starts, the plot panel must contain one tab.

*Parent: HLFR-00014*

### LLFR-00025 Add tab button
The plot panel must show a "+" button in the same row as the tabs, always directly to the right of the last tab.

Note: When the tabs are wider than the plot panel and the tab row shows scroll buttons, the "+" button is placed at the right end of the tab row, right after the scroll buttons, so that it stays visible and covers neither a tab nor a scroll button.

*Parent: HLFR-00015*

### LLFR-00026 Add tab button action
When the user clicks the "+" button (LLFR-00025), the app must add a new tab.

*Parent: HLFR-00015*

### LLFR-00027 Tab menu delete option
When the user right-clicks a tab, the app must show a menu with a "Delete" option.

*Parent: HLFR-00016*

### LLFR-00028 Delete tab action
When the user chooses "Delete" in the tab menu (LLFR-00027), the app must remove that tab.

*Parent: HLFR-00016*

### LLFR-00029 Tab menu rename option
When the user right-clicks a tab, the app must show a menu with a "Rename" option.

*Parent: HLFR-00017*

### LLFR-00030 Rename tab action
When the user chooses "Rename" in the tab menu (LLFR-00029), the app must let the user type a new name for that tab.

*Parent: HLFR-00017*

### LLFR-00031 Full tab blocks new plots
If the user tries to create a new plot in a tab that already holds the maximum number of plots (HLFR-00018), the app must not create the plot.

*Parent: HLFR-00018*

### LLFR-00032 Full tab notification
When the app does not create a plot because the tab is full (LLFR-00031), it must show the Full Tab Notification box, telling the user to add a new tab or delete a plot.

Note: The Full Tab Notification box is an information message, not an error box (HLFR-00002).

*Parent: HLFR-00018*

### LLFR-00033 Predefined curve colors
The first 8 signals drawn in a plot must use a predefined palette of 8 colors that are easy to tell apart.

*Parent: HLFR-00020*

### LLFR-00034 Random curve colors
From the 9th signal drawn in a plot onward, the app must give each new curve a randomly generated color that is different from the colors already used in that plot.

*Parent: HLFR-00020*

### LLFR-00035 Legend position
The legend must be placed directly above its plot.

*Parent: HLFR-00021*

### LLFR-00036 Legend names
The legend must show the names of the signals drawn in its plot.

*Parent: HLFR-00021*

### LLFR-00037 Legend colors
Each signal name in the legend must be shown in the same color as its curve.

*Parent: HLFR-00021*

### LLFR-00038 Curve menu delete option
When the user right-clicks a curve in a plot, the app must show a menu with a "Delete signal" option.

*Parent: HLFR-00022*

### LLFR-00039 Delete signal action
When the user chooses "Delete signal" in the curve menu (LLFR-00038), the app must remove that curve from the plot.

*Parent: HLFR-00022*

### LLFR-00040 Curve menu width option
When the user right-clicks a curve in a plot, the app must show a menu with a "Width" option that lists the preset widths 1 to 5.

*Parent: HLFR-00023*

### LLFR-00041 Set width action
When the user chooses a preset width in the "Width" option of the curve menu (LLFR-00040), the app must draw that curve with the chosen width.

*Parent: HLFR-00023*

### LLFR-00042 Hover tip
While the Tip button (LLFR-00018) is active and the user hovers over a curve, the app must show a tip with the x-axis and y-axis values of the hovered point.

*Parent: HLFR-00024*

### LLFR-00043 Tip x value
The tip must show the x-axis value in seconds.

*Parent: HLFR-00024, HLFR-00007*

### LLFR-00044 Tip y value
The tip must show the y-axis value as stored in the file, without a unit.

*Parent: HLFR-00024*

### LLFR-00045 Pin a tip
If the user left-clicks a curve while the hover tip (LLFR-00042) is shown, the app must fix the tip at that point in the plot.

*Parent: HLFR-00025*

### LLFR-00046 Pinned tip menu
When the user right-clicks a pinned tip, the app must show a menu with a "Delete" option.

*Parent: HLFR-00025*

### LLFR-00047 Remove a pinned tip
When the user chooses "Delete" in the pinned tip menu (LLFR-00046), the app must remove the pinned tip from the plot.

*Parent: HLFR-00025*

### LLFR-00048 Plot menu delete option
When the user right-clicks an empty area of a plot (not on a curve, a pinned tip or a vertical marker), the app must show a menu with a "Delete plot" option.

*Parent: HLFR-00019*

### LLFR-00049 Delete plot action
When the user chooses "Delete plot" in the plot menu (LLFR-00048), the app must remove that plot and all its curves from the tab.

*Parent: HLFR-00019*

### LLFR-00050 Space after deleting a plot
After a plot is deleted, the app must resize the remaining plots in the tab to fill the free space.

*Parent: HLFR-00019*

### LLFR-00051 Remove empty plot
When the last curve of a plot is removed (LLFR-00039), the app must delete that plot from the tab, as in LLFR-00049 and LLFR-00050.

*Parent: HLFR-00022, HLFR-00019*

### LLFR-00052 Default curve width
When the app draws a new curve, it must use preset width 1.

*Parent: HLFR-00023*

### LLFR-00066 Keep at least one tab
When the plot panel has only one tab, the app must show the "Delete" option of the tab menu (LLFR-00027) as disabled, so that the last tab cannot be deleted.

*Parent: HLFR-00016, HLFR-00014*

### LLFR-00067 Empty tab name
If the user enters a tab name that is empty or made only of spaces (LLFR-00030), the app must keep the tab's previous name and must not show any message.

*Parent: HLFR-00017*

### LLFR-00068 Time on the x-axis
Every plot must use the time signal (HLFR-00006) as its x-axis.

*Parent: HLFR-00012, HLFR-00013, HLFR-00007*

### LLFR-00069 Vertical stacking of plots
The plots in a tab must be stacked vertically, one below the other.

*Parent: HLFR-00014, HLFR-00018*

### LLFR-00070 Shared time axis
The plots in a tab must share the same x-axis range, so that a change to the time range of one plot applies to all plots in that tab.

*Parent: HLFR-00014*

### LLFR-00074 Mouse wheel zoom
When the user turns the mouse wheel over a plot, the app must zoom in the plot's x-axis when the wheel turns forward and zoom out when it turns backward, centered on the time under the mouse pointer.

*Parent: HLFR-00027*

### LLFR-00075 Zoom on the x-axis only
The user must not be able to zoom the y-axis of a plot.

Note: The app still adjusts the y-axis range by itself, as described in LLFR-00076.

*Parent: HLFR-00027*

### LLFR-00076 Curves visible at any zoom
After every zoom, the app must set the y-axis range of each plot so that every curve in that plot is fully visible within the shown x-axis range.

*Parent: HLFR-00027*

### LLFR-00078 Click to zoom
While the Zoom button (LLFR-00077) is active and the user left-clicks a plot, the app must zoom in the plot's x-axis by a factor of 2, centered on the time of the clicked point.

*Parent: HLFR-00027*

### LLFR-00081 Place a marker by click
While the Vertical marker button (LLFR-00080) is active and the user left-clicks a plot anywhere other than on an existing vertical marker, the app must draw a new vertical marker in that plot at the time of the clicked point.

*Parent: HLFR-00028*

### LLFR-00082 Marker height
A vertical marker must cover the whole y-axis range shown in its plot, and must keep covering it when that range changes.

*Parent: HLFR-00028*

### LLFR-00083 Marker color
The app must draw vertical markers in a reserved marker color that it never uses for curves (LLFR-00033, LLFR-00034).

*Parent: HLFR-00028, HLFR-00020*

### LLFR-00084 Marker label
The app must show the name of a vertical marker in a label at the top of its line.

*Parent: HLFR-00028*

### LLFR-00085 Default marker name
The app must name each new vertical marker "Marker N", where N is 1 for the first marker placed in that plot and grows by 1 for each new marker in that plot.

*Parent: HLFR-00028*

### LLFR-00086 Drag a marker
While the Vertical marker button (LLFR-00080) is active and the user presses the left mouse button on a vertical marker and drags it, the app must move the marker along the x-axis with the mouse pointer and leave it at the time where the button is released.

*Parent: HLFR-00029*

### LLFR-00087 Marker menu rename option
When the user right-clicks a vertical marker, the app must show a menu with a "Rename" option.

*Parent: HLFR-00030*

### LLFR-00088 Rename marker action
When the user chooses "Rename" in the marker menu (LLFR-00087), the app must let the user type a new name for that marker.

*Parent: HLFR-00030*

### LLFR-00089 Empty marker name
If the user enters a marker name that is empty or made only of spaces (LLFR-00088), the app must keep the marker's previous name and must not show any message.

*Parent: HLFR-00030*

### LLFR-00090 Marker menu delete option
When the user right-clicks a vertical marker, the app must show a menu with a "Delete" option.

*Parent: HLFR-00031*

### LLFR-00091 Delete marker action
When the user chooses "Delete" in the marker menu (LLFR-00090), the app must remove that marker and its label from the plot.

*Parent: HLFR-00031*

### LLFR-00092 Marker time value
The app must show the time of a vertical marker, in seconds, directly below the marker's label (LLFR-00084).

*Parent: HLFR-00028, HLFR-00007*

### LLFR-00093 Marker time value while dragging
While the user drags a vertical marker (LLFR-00086), the app must update the marker's time value (LLFR-00092) to the marker's current position.

*Parent: HLFR-00029*

### LLFR-00106 Tab alignment
The tabs must be aligned to the left of the top edge of the plot panel, with the first tab starting at the panel's left edge.

*Parent: HLFR-00014*

### LLFR-00107 Add tab button style
The "+" button (LLFR-00025) must have the same height, background, border and corner shape as an unselected tab, and must be narrower than a tab, like the new tab button of a modern web browser.

*Parent: HLFR-00015*

### LLFR-00108 Wheel zoom with any plot tool
The app must apply mouse wheel zoom (LLFR-00074) whether or not a plot tool is active.

Note: Mouse wheel zoom is not a plot tool (HLFR-00032).

*Parent: HLFR-00027, HLFR-00032*

### LLFR-00110 Marker menu over a curve
When the user right-clicks a point where a vertical marker overlaps a curve, the app must show the marker menu (LLFR-00087, LLFR-00090) and not the curve menu (LLFR-00038, LLFR-00040).

*Parent: HLFR-00030, HLFR-00031*

### LLFR-00111 Marker numbers not reused
The app must not reuse the number of a deleted vertical marker (LLFR-00085) for a new marker in the same plot.

*Parent: HLFR-00028*

### LLFR-00112 Renamed marker label
After the user types a new marker name (LLFR-00088), the app must show the new name in the marker's label (LLFR-00084).

*Parent: HLFR-00030*
