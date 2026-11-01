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

### LLFR-00280 Resize border highlight
While the mouse pointer is over the part of the border between the plot panel and the signal list panel where a drag changes their widths (LLFR-00073), and while the user drags that border, the app must draw a blue vertical line, 2 pixels wide, along the border over the full height of the two panels. The app must hide the line as soon as the pointer is no longer over that part of the border and no drag is in progress.

Note: The line is hidden the rest of the time, so the border is visible only when the user can use it.

*Parent: HLFR-00026*

### LLFR-00281 Resize pointer
While the mouse pointer is over the part of the border of LLFR-00280, and while the user drags it, the app must show the mouse pointer as a horizontal resize pointer.

*Parent: HLFR-00026*

### LLFR-00138 Undo action
When the user clicks the Undo button (LLFR-00136) or presses its shortcut (LLFR-00137), the app must reverse the most recent undoable action (LLFR-00140) that has not been undone yet, returning the tabs, plots, curves, data tips and markers to the state they were in before that action.

*Parent: HLFR-00040*

### LLFR-00139 Undo depth
The app must keep only the 30 most recent undoable actions for undo, so that the user can undo at most 30 actions in a row.

*Parent: HLFR-00040*

### LLFR-00140 Undoable actions
The app must treat these actions as undoable: adding a tab, deleting a tab, renaming a tab, creating a plot, deleting a plot, adding a curve to a plot, removing a curve from a plot, changing a curve's width, pinning a data tip, moving a pinned data tip, deleting a pinned data tip, placing a vertical marker, moving a vertical marker, renaming a vertical marker, deleting a vertical marker, placing a delta marker and deleting a delta marker.

Note: Removing a curve also removes its delta markers (LLFR-00178), and undoing the removal brings them back. Opening a file, zooming, panning, resetting the zoom, showing or hiding the grid, exporting, copying, searching and resizing the panels are not undoable. Saving and loading a layout (LLFR-00238) are not undoable either. Creating and deleting a synthetic signal (LLFR-00255) are not undoable either.

*Parent: HLFR-00040*

### LLFR-00142 Undo history on file open
When the app opens a file or replaces the current file (LLFR-00013), it must clear the undo history and the redo history (LLFR-00192).

*Parent: HLFR-00040, HLFR-00010, HLFR-00048*

### LLFR-00192 Redo action
When the user clicks the Redo button (LLFR-00190) or presses its shortcut (LLFR-00191), the app must reapply the most recently undone action (LLFR-00138) that has not been redone yet, returning the tabs, plots, curves, data tips and markers to the state they were in after that action, and must make that action available to undo again.

Note: The user can redo, one by one, every action undone since the last new undoable action, so at most 30 (LLFR-00139).

*Parent: HLFR-00048*

### LLFR-00193 New action clears redo
When the user does an undoable action (LLFR-00140) after undoing, the app must discard all undone actions, so that they can no longer be redone.

*Parent: HLFR-00048*

### LLFR-00195 Redo shortcut while typing
While the keyboard focus is in a text field (LLFR-00157), the Redo shortcut (LLFR-00191) must not redo actions on the tabs, plots, curves, data tips and markers.

Note: This lets Ctrl+Y act on the text being typed, as text fields usually do.

*Parent: HLFR-00048*

### LLFR-00196 Undo shortcut while typing
While the keyboard focus is in a text field (LLFR-00157), the Undo shortcut (LLFR-00137) must not undo actions on the tabs, plots, curves, data tips and markers.

Note: This lets Ctrl+Z (Cmd+Z on macOS) act on the text being typed, as text fields usually do.

*Parent: HLFR-00040*

### LLFR-00182 Where the app icon is shown
The app must show its icon (HLFR-00045), instead of the default PyInstaller or Python icon, as the icon of the standalone executable (COR-00007), in the list of open apps (the Dock and the app switcher on macOS, the taskbar on Windows), and in the main window's title bar where the operating system shows an icon there.

*Parent: HLFR-00045*

### LLFR-00183 App icon picture
The app icon must show a small line chart with a blue curve and a red curve (LLFR-00144) over a pair of axes, on a light rounded square, and must stay recognizable at 16 by 16 pixels.

*Parent: HLFR-00045*

### LLFR-00184 Splash screen at launch
When the user launches the app, the app must show the splash screen (HLFR-00046) within 2 seconds, before the main window is ready.

*Parent: HLFR-00046*

### LLFR-00185 Splash screen content
The splash screen must show the app icon (LLFR-00183), the app name "plot_tool" and the text "Loading...".

*Parent: HLFR-00046, HLFR-00045*

### LLFR-00186 Splash screen closes
When the main window is shown, the app must close the splash screen.

*Parent: HLFR-00046*

### LLFR-00187 Splash screen on a startup error
If an error stops the app from starting, the app must close the splash screen before it shows the error box (HLFR-00002).

*Parent: HLFR-00046, HLFR-00002*

### LLFR-00188 Opening time limit
The standalone executable (COR-00007) must show the main window, ready to respond to the user, at most 5 seconds after the user launches it.

Note: The time is measured from the second launch onward, on the computer the app is tested on, so that work done only once on the first launch does not count.

*Parent: HLFR-00047*

### LLFR-00189 No repeated startup work
The app must not repeat on every launch work whose result does not change between launches.

Note: For example, the cache of fonts used to draw text in the plots is built on every launch today; it must be built once and reused.

*Parent: HLFR-00047*


## Top panel

### LLFR-00004 Open file button
The top panel must contain a button called "Open file".

*Parent: HLFR-00004*

### LLFR-00005 File selection dialog
When the user clicks the open file button (LLFR-00004), the app must show a file selection dialog.

*Parent: HLFR-00004*

### LLFR-00204 File dialog starting folder
The first time the user clicks the Open file button after the app starts, the file selection dialog (LLFR-00005) must show the folder that contains the standalone executable (COR-00007): the folder that holds `plot_tool.app` on macOS, or the folder that holds the executable on Windows. When the app runs from source, the first folder must be the repository folder. After that, it must show the folder of the last file the app opened successfully.

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

### LLFR-00018 Data tip button
The top panel must contain a button called "Data tip".

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

### LLFR-00114 Reset zoom button
The top panel must contain a button called "Reset zoom".

*Parent: HLFR-00035*

### LLFR-00116 Reset zoom button feedback
When the user clicks the Reset zoom button, the button must show its active color (LLFR-00001) until the zoom reset (LLFR-00115) has finished, and for at least 0.3 seconds, and must then return to its normal color (LLFR-00003).

*Parent: HLFR-00035, HLFR-00003*

### LLFR-00207 Z key resets the zoom
When the user presses the Z key alone, with no other keyboard key, the app must reset the zoom as if the Reset zoom button were clicked (LLFR-00115, LLFR-00116). While the user is dragging the mouse (a pan, a marker or data tip drag, or a time span selection), the Z key must do nothing.

Note: Ctrl+Z and Cmd+Z stay Undo (LLFR-00137).

*Parent: HLFR-00035*

### LLFR-00121 Grid button
The top panel must contain a button called "Grid".

*Parent: HLFR-00037*

### LLFR-00124 Grid button state
While the grid is shown, the Grid button must show its active color (LLFR-00001).

*Parent: HLFR-00037, HLFR-00003*

### LLFR-00126 Export button
The top panel must contain a button called "Export".

*Parent: HLFR-00038*

### LLFR-00127 Export menu PDF option
When the user clicks the Export button, the app must show a menu with a "Save all tabs as PDF" option.

*Parent: HLFR-00038*

### LLFR-00128 PDF save dialog
When the user chooses "Save all tabs as PDF" (LLFR-00127), the app must show a save file dialog for a `.pdf` file.

*Parent: HLFR-00038*

### LLFR-00129 PDF content
The saved PDF must have one page for each tab that holds at least one plot, in tab order, with the tab's name at the top of the page and the tab's plots below it as they are shown on screen, including their time range, curves, legends, grid, vertical markers, delta markers and pinned data tips.

*Parent: HLFR-00038*

### LLFR-00130 Export cancelled
If the user cancels the save file dialog (LLFR-00128), the app must not save any file.

*Parent: HLFR-00038*

### LLFR-00131 Export failure
If the PDF file cannot be written, the app must show an error box saying that the file could not be saved.

*Parent: HLFR-00038, HLFR-00002*

### LLFR-00132 Copy button
The top panel must contain a button called "Copy".

*Parent: HLFR-00039*

### LLFR-00133 Copy action
When the user clicks the Copy button, the app must put on the system clipboard an image of all plots of the current tab as they are shown on screen.

*Parent: HLFR-00039*

### LLFR-00134 HDF5 file signals
In HDF5 files, the app must read each dataset that holds a one-dimensional numeric array as one signal, in any group, named after the dataset's path in the file without the leading `/` (for example `engine/speed`).

Note: The time signal (HLFR-00006) is therefore a dataset named `Time` at the top level of the file. Reading HDF5 needs a new library (COR-00011).

*Parent: HLFR-00005*

### LLFR-00135 Other HDF5 datasets
In HDF5 files, the app must ignore datasets that do not hold a one-dimensional numeric array, and must apply the checks of HLFR-00008 and HLFR-00009 only to the signals it read.

*Parent: HLFR-00005, HLFR-00008, HLFR-00009*

### LLFR-00136 Undo button
The top panel must contain a button called "Undo".

*Parent: HLFR-00040*

### LLFR-00137 Undo shortcut
The app must run the Undo button's action (LLFR-00138) when the user presses Ctrl+Z (Cmd+Z on macOS), except as in LLFR-00196.

*Parent: HLFR-00040*

### LLFR-00141 Undo unavailable
When no action is left to undo (LLFR-00139), the app must show the Undo button as disabled, in a paler color, and neither the button nor its shortcut must do anything.

*Parent: HLFR-00040, HLFR-00003*

### LLFR-00190 Redo button
The top panel must contain a button called "Redo", placed directly to the right of the Undo button (LLFR-00136).

*Parent: HLFR-00048*

### LLFR-00191 Redo shortcut
The app must run the Redo button's action (LLFR-00192) when the user presses Ctrl+Y (Cmd+Y on macOS), except as in LLFR-00195.

*Parent: HLFR-00048*

### LLFR-00194 Redo unavailable
When no undone action is left to redo, the app must show the Redo button as disabled, in a paler color, and neither the button nor its shortcut must do anything.

*Parent: HLFR-00048, HLFR-00003*

### LLFR-00145 Nothing to export
If no tab holds a plot when the user chooses "Save all tabs as PDF", the app must show an information box saying that there are no plots to export, and must not show the save file dialog.

*Parent: HLFR-00038*

### LLFR-00146 Nothing to copy
If the current tab holds no plot when the user clicks the Copy button, the app must show an information box saying that there are no plots to copy, and must not change the clipboard.

*Parent: HLFR-00039*

### LLFR-00148 Hold the Data tip key
While the user holds down the Data tip key alone, with no other keyboard key, the app must keep the Data tip button (LLFR-00018) active, deactivating any other plot tool as in LLFR-00079.

Note: The **Data tip key** is the Command key on macOS and the Ctrl key on Windows.

*Parent: HLFR-00024, HLFR-00032*

### LLFR-00149 Release the Data tip key
When the user releases the Data tip key after LLFR-00148, the app must deactivate the Data tip button, so that no plot tool is active, whatever plot tool was active before the Data tip key was pressed.

*Parent: HLFR-00024, HLFR-00032*

### LLFR-00150 Data tip key with another key
If the user presses another keyboard key while holding the Data tip key (for example Cmd+Z, Ctrl+Z or Ctrl+Y), the app must end the Data tip activation of LLFR-00148 as in LLFR-00149.

*Parent: HLFR-00024, HLFR-00032*

### LLFR-00154 Hold the Shift key
While the user holds down the Shift key alone, with no other keyboard key, the app must keep the Vertical marker button (LLFR-00080) active, deactivating any other plot tool as in LLFR-00079.

*Parent: HLFR-00028, HLFR-00032*

### LLFR-00155 Release the Shift key
When the user releases the Shift key after LLFR-00154, the app must deactivate the Vertical marker button, so that no plot tool is active, whatever plot tool was active before the Shift key was pressed.

*Parent: HLFR-00028, HLFR-00032*

### LLFR-00156 Shift key with another key
If the user presses another keyboard key while holding the Shift key (for example Shift+A), the app must end the Vertical marker activation of LLFR-00154 as in LLFR-00155.

*Parent: HLFR-00028, HLFR-00032*

### LLFR-00197 Hold the X key
While the user holds down the X key alone, with no other keyboard key, the app must keep the Delta X button (LLFR-00161) active, deactivating any other plot tool as in LLFR-00079.

*Parent: HLFR-00043, HLFR-00032*

### LLFR-00198 Release the X key
When the user releases the X key after LLFR-00197, the app must deactivate the Delta X button, so that no plot tool is active, whatever plot tool was active before the X key was pressed.

*Parent: HLFR-00043, HLFR-00032*

### LLFR-00199 X key with another key
If the user presses another keyboard key while holding the X key, the app must end the Delta X activation of LLFR-00197 as in LLFR-00198.

*Parent: HLFR-00043, HLFR-00032*

### LLFR-00200 Hold the Y key
While the user holds down the Y key alone, with no other keyboard key, the app must keep the Delta Y button (LLFR-00162) active, deactivating any other plot tool as in LLFR-00079.

*Parent: HLFR-00044, HLFR-00032*

### LLFR-00201 Release the Y key
When the user releases the Y key after LLFR-00200, the app must deactivate the Delta Y button, so that no plot tool is active, whatever plot tool was active before the Y key was pressed.

*Parent: HLFR-00044, HLFR-00032*

### LLFR-00202 Y key with another key
If the user presses another keyboard key while holding the Y key, the app must end the Delta Y activation of LLFR-00200 as in LLFR-00201.

*Parent: HLFR-00044, HLFR-00032*

### LLFR-00157 Plot tool keys while typing
While the keyboard focus is in a text field (the search box, or a field where the user types a tab or marker name), the app must not apply LLFR-00148, LLFR-00154, LLFR-00197, LLFR-00200 or LLFR-00207.

Note: This lets the user type capital letters and use keyboard shortcuts in text fields without activating a plot tool.

*Parent: HLFR-00024, HLFR-00028, HLFR-00032*

### LLFR-00158 Icon instead of the name
Each button in the top panel must show only its icon, without its name written on the button.

Note: The name a button is "called" in the other requirements (for example "Open file" in LLFR-00004) is the name shown in its button tip (LLFR-00181).

*Parent: HLFR-00042*

### LLFR-00159 Icon pictures
The app must show these icons, the same on every operating system:
1. Open file: an open folder;
2. Undo: an arrow curving to the left;
3. Data tip: a callout box pointing at a dot on a curve;
4. Zoom: a magnifying glass with a plus sign;
5. Reset zoom: a magnifying glass with two arrows pointing away from each other, to the left and to the right;
6. Vertical marker: a dashed vertical line with a small flag at its top;
7. Delta X: a horizontal double-headed arrow between two vertical lines;
8. Delta Y: a vertical double-headed arrow between two horizontal lines;
9. Grid: a square divided into 3 by 3 cells;
10. Export: a sheet of paper with an arrow pointing out of it;
11. Copy: two overlapping sheets of paper;
12. Redo: an arrow curving to the right;
13. Save layout: a sheet of paper with two small stacked plots and an arrow pointing down into it;
14. Load layout: a sheet of paper with two small stacked plots and an arrow pointing up out of it.

*Parent: HLFR-00042, HLFR-00048, HLFR-00049, HLFR-00050*

### LLFR-00160 Icon visibility
Each icon must be clearly visible against its button's background in the normal, active (LLFR-00001) and disabled (LLFR-00141) states, and must be shown paler while the button is disabled.

*Parent: HLFR-00042, HLFR-00003*

### LLFR-00161 Delta X button
The top panel must contain a button called "Delta X".

*Parent: HLFR-00043, HLFR-00032*

### LLFR-00162 Delta Y button
The top panel must contain a button called "Delta Y".

*Parent: HLFR-00044, HLFR-00032*

### LLFR-00181 Button name on hover
When the user holds the mouse pointer over a button in the top panel, the app must show a button tip with the button's name next to the pointer, and must hide it when the pointer leaves the button.

Note: This helps a user who is starting to use the app to learn what each icon does.

*Parent: HLFR-00042*

### LLFR-00213 Shortcut in the button tip
When a top panel button has a keyboard shortcut, its button tip (LLFR-00181) must show the shortcut on a second line, below the button's name, in a paler color than the name.

*Parent: HLFR-00042*

### LLFR-00214 Mouse use in the button tip
When a top panel button has no keyboard shortcut but its tool is used with the mouse on the plots, its button tip (LLFR-00181) must show, on one or two lines below the button's name and in a paler color than the name, a summary of a few words of how to use the tool with the mouse or the trackpad.

*Parent: HLFR-00042*

### LLFR-00215 Button tip texts
The line below the name in the button tip of each button with a shortcut (LLFR-00213) must be, on macOS and on Windows:

| Button | macOS | Windows |
|---|---|---|
| Undo | Cmd+Z | Ctrl+Z |
| Redo | Cmd+Y | Ctrl+Y |
| Data tip | Hold Cmd | Hold Ctrl |
| Vertical marker | Hold Shift | Hold Shift |
| Delta X | Hold X | Hold X |
| Delta Y | Hold Y | Hold Y |
| Reset zoom | Z | Z |

The button tip of the Zoom button (LLFR-00214) must show two lines below its name, on macOS and on Windows: "Click or drag to zoom in" and "Wheel or two-finger swipe to zoom in or out".

The button tips of the Open file, Save layout, Load layout, Grid, Export and Copy buttons must show only the button's name.

Note: The texts follow LLFR-00137, LLFR-00191, LLFR-00148, LLFR-00154, LLFR-00197, LLFR-00200, LLFR-00207, LLFR-00078, LLFR-00208, LLFR-00074 and LLFR-00206. When a shortcut or a mouse use changes, its button tip text must change with it.

*Parent: HLFR-00042*

### LLFR-00216 Save layout button
The top panel must contain a button called "Save layout", placed directly to the right of the Open file button (LLFR-00004).

*Parent: HLFR-00049*

### LLFR-00217 Load layout button
The top panel must contain a button called "Load layout", placed directly to the right of the Save layout button (LLFR-00216).

*Parent: HLFR-00050*

### LLFR-00218 Layout buttons need a data file
While no data file is open, the app must show the Save layout and Load layout buttons as disabled, in a paler color, and neither button must do anything.

*Parent: HLFR-00049, HLFR-00050, HLFR-00003*

### LLFR-00219 Save layout dialog
When the user clicks the Save layout button, the app must show a save file dialog in which the user chooses the folder and types the name of the layout file. If the typed name has no extension, the app must add `.json`.

*Parent: HLFR-00049*

### LLFR-00220 Layout dialog starting folder
The first time after the app starts that the user clicks the Save layout or Load layout button, the dialog (LLFR-00219, LLFR-00221) must show the folder that the file selection dialog of the Open file button would show at that moment (LLFR-00204). After that, it must show the folder of the last layout file that the app saved or loaded successfully.

*Parent: HLFR-00049, HLFR-00050*

### LLFR-00221 Load layout dialog
When the user clicks the Load layout button, the app must show a file selection dialog that lists the layout files (`.json`), in which the user chooses the layout file to load.

*Parent: HLFR-00050*

### LLFR-00222 Layout dialog cancelled
If the user cancels the dialog of LLFR-00219 or LLFR-00221, the app must not save or load any file and must keep the current layout unchanged.

*Parent: HLFR-00049, HLFR-00050*

### LLFR-00223 Replace an existing layout file
If the user chooses the name of a file that already exists in the dialog of LLFR-00219, the app must ask the user whether to replace it, and must save the layout only if the user agrees.

*Parent: HLFR-00049*

### LLFR-00224 Layout save failure
If the layout file cannot be written, the app must show an error box saying that the layout file could not be saved.

*Parent: HLFR-00049, HLFR-00002*

### LLFR-00225 Layout file content
The layout file must hold:
1. the names of the tabs, in tab order, and which tab is shown;
2. for each tab, its plots, from top to bottom;
3. for each plot, its curves, in the order they were drawn, each with its signal name, color and width;
4. the x-axis range shared by the plots (LLFR-00070), in seconds;
5. whether the grid is shown (HLFR-00037);
6. for each vertical marker, its name and time;
7. for each pinned data tip, its plot, the signal and time of its point, and its position relative to the point;
8. for each delta marker, its plot, whether it is a Delta X or a Delta Y marker, and the signal and time of each of its two points;
9. the widths of the plot panel and the signal list panel;
10. for each synthetic signal, in the order it was created, its current name, its operation, the current names of the signals it was computed from, and its parameter: the cutoff frequency, the filter order and how the filter starts (Low-pass and High-pass filters), the window size (Moving average), the constant (Comparison operations and Arithmetic operations with a constant) or the time range (FFT).

*Parent: HLFR-00049, HLFR-00056*

### LLFR-00226 Not in the layout file
The layout file must not hold the name or the path of the data file, the undo and redo history, the active plot tool or the text of the search box.

*Parent: HLFR-00049*

### LLFR-00227 Layout file format
The app must write the layout file as JSON text in UTF-8, indented by 2 spaces, with each value on its own line, with keys that are English words describing their value (for example `tabs`, `plots`, `signal`, `width`), and with each time in seconds written as a decimal number with enough digits to be read back as the same value.

Note: JSON can be read and written with Python's standard library, so no new library is needed (COR-00011), and text editors such as Notepad++ highlight it.

*Parent: HLFR-00051*

### LLFR-00228 Layout file identification
The layout file must start with an entry `format` with the value `plot_tool layout` and an entry `version` with the number of the layout file format, so that the app can tell a layout file from other JSON files.

*Parent: HLFR-00051, HLFR-00050*

### LLFR-00229 Layout added in new tabs
When the user loads a layout file (LLFR-00221) and the current tabs hold at least one plot, the app must keep the current tabs, with their plots, curves, pinned data tips and delta markers, unchanged, and must add the tabs of the layout file after the last current tab. When no current tab holds a plot, the app must replace the current tabs with the tabs of the layout file. In both cases, the app must show the first tab of the layout file.

Note: Loading a layout never asks for confirmation, because it removes no plot.

*Parent: HLFR-00050*

### LLFR-00230 Rebuild the layout
When the app loads a layout file, it must build the tabs, plots, curves, delta markers and pinned data tips of the file in the file's order, in the tabs of LLFR-00229, add the vertical markers of the file to the current ones (LLFR-00205), and apply the file's time range to every plot (LLFR-00070), the file's grid setting to every plot (LLFR-00122, LLFR-00123) and the file's panel widths, using the signals of the opened data file and the synthetic signals of LLFR-00262, except as in LLFR-00231 to LLFR-00235.

*Parent: HLFR-00050*

### LLFR-00231 Missing signals in a layout
When loading a layout, the app must not draw a curve whose signal is not in the opened data file, must not create a plot that is left with no curve, and must still create every tab of the file, even one left with no plot.

*Parent: HLFR-00050, HLFR-00052*

### LLFR-00232 Data tips and delta markers in a layout
When loading a layout, the app must rebuild a pinned data tip or a delta marker only if the signal of each of its points is drawn in its plot and has a sample whose time differs from the saved time by at most 1 microsecond, and must place each point on that sample.

*Parent: HLFR-00050, HLFR-00052*

### LLFR-00233 Vertical markers in a layout
When loading a layout, the app must rebuild a vertical marker only if its time is within the time range of the opened data file.

*Parent: HLFR-00050, HLFR-00052*

### LLFR-00234 Time range in a layout
When loading a layout, the app must limit the saved x-axis range to the time range of the opened data file (LLFR-00119). If the saved range does not overlap the file's time range, the app must show the whole time range of the file.

*Parent: HLFR-00050, HLFR-00052*

### LLFR-00235 Unusable values in a layout
When loading a layout, the app must replace a value it cannot use with the value it would use for a new item: a curve width that is not one of the preset widths 1 to 5 with width 1 (LLFR-00052), a color that is not valid or is already used in the plot with the next color of LLFR-00033 and LLFR-00034, and a tab name that is empty, is not a text or is the name of an earlier tab of the same layout file with a name as in LLFR-00210. It must not create the plots of a tab beyond the maximum of HLFR-00018. A tab name of the file that is valid but is already the name of another tab, for example a kept tab (LLFR-00229), must also be replaced with a name as in LLFR-00210, but this replacement must not be listed in the load report and must not on its own cause the report to be shown (LLFR-00237).

Note: Such values appear only when the file was edited by hand.

*Parent: HLFR-00050, HLFR-00052*

### LLFR-00236 Unreadable layout file
If the chosen file cannot be read, is not valid JSON or does not identify itself as a layout file (LLFR-00228), the app must show an error box saying that the file could not be read as a layout file, and must keep the current layout unchanged.

*Parent: HLFR-00050, HLFR-00002*

### LLFR-00237 Layout load report
After loading a layout, if any part of it was not rebuilt or was changed (LLFR-00231 to LLFR-00235, LLFR-00262), the app must show one information box that lists: the signals that are not in the data file, each named once; each synthetic signal that was not created, with the reason; each pinned data tip, vertical marker and delta marker that was not rebuilt, with its time and the reason; the time range when it was changed; and each value that was replaced. If everything was rebuilt as saved, the app must not show any message.

Note: The box is an information box, not an error box (HLFR-00002), like the Full Tab Notification box (LLFR-00032). A long list must be scrollable.

*Parent: HLFR-00052*

### LLFR-00238 Undo history on layout load
When the app loads a layout, it must clear the undo and redo history (LLFR-00142). Saving and loading a layout must not be undoable actions (LLFR-00140).

*Parent: HLFR-00050, HLFR-00040, HLFR-00048*

### LLFR-00262 Synthetic signals on layout load
When the app loads a layout file (LLFR-00230), before it rebuilds the plots, it must remove the current synthetic signals and create the synthetic signals of the file, in the file's order and with their saved names, using the saved operation, signals and parameter (LLFR-00225), and, for an FFT, the saved time range limited to the time range of the opened data file. A synthetic signal must not be created when a signal it is computed from is missing, when its parameter is not allowed (LLFR-00245, LLFR-00269, LLFR-00272), when the operation cannot be done (LLFR-00247, LLFR-00250), or when its saved name is the name of a signal of the data file. Its curves must then be treated as curves of a missing signal (LLFR-00231), and the load report (LLFR-00237) must name it with the reason.

*Parent: HLFR-00056, HLFR-00050, HLFR-00052*

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

### LLFR-00239 Synthetic signal menu
When the user right-clicks a signal name in the signal list panel, the app must show a menu with a "Create synthetic signal" option that lists the operations of LLFR-00268, showing only these operation names and not the names the new signals will have (LLFR-00240). Choosing an operation must create the synthetic signal of that operation from the right-clicked signal.

*Parent: HLFR-00053*

### LLFR-00240 Synthetic signal names
The app must name a synthetic signal with the operation name `integral`, `derivative`, `lowpass`, `highpass`, `movingaverage`, `max`, `min`, `greater`, `less`, `greaterorequal`, `lessorequal`, `add`, `subtract`, `multiply`, `divide`, `product` or `fft`, an underscore and the full current name of the signal it was computed from. When that signal is itself a synthetic signal, its whole name is used, so that the operations build up from left to right, for example `integral_Speed`, `derivative_integral_Speed` or `fft_lowpass_Speed_1.5s_to_3s`. A Product with signal must be named `product`, an underscore, the full current name of the right-clicked signal, an underscore and the full current name of the second signal (LLFR-00275), for example `product_Speed_Torque`.

An FFT signal's name must end with an underscore and its time range (LLFR-00248), written as `<start>s_to_<end>s`, with the start and end times in seconds in the same number format as the data tip's x value (LLFR-00043), for example `fft_Speed_1.5s_to_3s`. Two FFTs of the same signal over different time ranges therefore get different names.

*Parent: HLFR-00054*

### LLFR-00264 Synthetic signals from synthetic signals
The app must let the user create a synthetic signal from a synthetic signal in the same way as from a signal of the data file (LLFR-00239), except as in LLFR-00251.

*Parent: HLFR-00053*

### LLFR-00241 Synthetic signal name already used
If the name of LLFR-00240 is already the name of a signal in the signal list, the app must add an underscore and the smallest number from 2 up that makes the name unique, for example `lowpass_Speed_2`.

Note: This happens, for example, when the same signal is filtered twice with different cutoff frequencies or filter orders, or compared with two different constants.

*Parent: HLFR-00054*

### LLFR-00242 Synthetic signals in the signal list
The signal list panel must show the synthetic signals after the signals of the data file, in the order they were created, in italic letters, and the user must be able to search for them (HLFR-00033) and plot them (LLFR-00019, LLFR-00021) like the signals of the data file, except as in LLFR-00257.

*Parent: HLFR-00053, HLFR-00011*

### LLFR-00243 Integral
The Integral of a signal must have, at each time sample, the integral of the signal over time from the first time sample up to that sample, computed with the trapezoidal rule, so that its first sample is 0.

*Parent: HLFR-00053*

### LLFR-00244 Derivative
The Derivative of a signal must have, at each time sample, the rate of change of the signal with respect to time, computed from the neighboring samples on both sides, and from the one neighbor at the first and last samples.

*Parent: HLFR-00053*

### LLFR-00245 Filter dialog
When the user chooses "Low-pass filter" or "High-pass filter" (LLFR-00239), the app must show a dialog that asks for the cutoff frequency in Hz and for the filter order, and states both allowed ranges: for the cutoff frequency, greater than 0 and less than half the sampling rate (LLFR-00247); for the order, a whole number from 1 to 8. The dialog must show 2 as the starting value of the order. The dialog must also let the user choose how the filter starts (LLFR-00246), with two choices, "From the first value" and "From zero", and "From the first value" chosen when the dialog opens. The app must create the filtered signal only when the user confirms a cutoff frequency and an order in their allowed ranges. If a value is outside its range or not a number, the dialog must stay open and say why. If the user cancels the dialog, the app must not create any signal.

*Parent: HLFR-00053*

### LLFR-00246 Filter type
The Low-pass filter and the High-pass filter must be Butterworth filters of the order of LLFR-00245, with its cutoff frequency, applied once over the signal, forward in time, as a real-time filter would be, so that the filtered curve is delayed like the output of a real filter. The filter must start as the user chose in the dialog of LLFR-00245: with "From the first value", as if the signal had kept the value of its first sample before the first sample (steady-state initial conditions), so that the filtered curve starts in sync with the first value and does not jump at the start; with "From zero", at rest (zero initial state), as if the signal had been 0 before the first sample, like a real filter switched on at the first sample, so that the filtered curve settles after the start.

Note: With "From the first value", a constant signal stays unchanged through a Low-pass filter and gives 0 through a High-pass filter, from the first sample on. With "From zero", a constant signal gives a Low-pass output that starts below the constant and rises towards it, and a High-pass output that starts at a part of the constant (close to it when the cutoff frequency is well below half the sampling rate) and decays towards 0.

*Parent: HLFR-00053*

### LLFR-00247 Evenly spaced time samples
The app must compute the sampling rate as 1 divided by the mean time step of the time signal. If any time step differs from the mean time step by more than 1%, the app must not create a Low-pass filter, High-pass filter or FFT signal, and must show an information box saying that the operation needs evenly spaced time samples.

*Parent: HLFR-00053*

### LLFR-00248 FFT time range
The FFT must use only the samples of the signal whose time is within the x-axis range shared by the time plots (LLFR-00070) when the FFT is created, or all samples when no time plot exists. A later change of the time range must not change the FFT signal.

*Parent: HLFR-00057*

### LLFR-00249 FFT result
The FFT signal must be the one-sided amplitude spectrum of the samples of LLFR-00248, from 0 Hz up to half the sampling rate (LLFR-00247), computed with a Hann window and scaled so that a sine wave of amplitude A over the whole time range gives a peak of height close to A.

*Parent: HLFR-00053, HLFR-00057*

### LLFR-00250 Too few samples for an FFT
If fewer than 8 samples of the signal are within the time range of LLFR-00248, the app must not create the FFT signal and must show an information box saying that the time range holds too few samples.

*Parent: HLFR-00053, HLFR-00057*

### LLFR-00251 No operations on FFT signals
When the user right-clicks an FFT signal, the app must show the "Create synthetic signal" option (LLFR-00239) as disabled.

Note: An FFT signal has frequency, not time, on its x-axis, so the operations do not apply to it.

*Parent: HLFR-00053*

### LLFR-00252 Synthetic signals on file replace
When the app opens a data file or replaces the current one (LLFR-00013), it must remove every synthetic signal of the previous data file.

*Parent: HLFR-00053, HLFR-00010*

### LLFR-00253 Data file unchanged
The app must never write synthetic signals, or anything else, to the data file. Synthetic signals must exist only in the app's memory, until they are deleted (LLFR-00255), the data file is replaced (LLFR-00252) or the app is closed.

Note: A layout file can create them again (LLFR-00262).

*Parent: HLFR-00055*

### LLFR-00254 Delete synthetic signal option
When the user right-clicks a synthetic signal in the signal list panel, the app must show a "Delete signal" option in the menu of LLFR-00239. The menu of a signal of the data file must not have this option.

*Parent: HLFR-00059*

### LLFR-00255 Delete synthetic signal action
When the user chooses "Delete signal" (LLFR-00254), the app must ask the user whether to proceed, naming the synthetic signals that were computed from it, directly or through other synthetic signals. If the user proceeds, the app must remove the signal and those synthetic signals from the signal list, remove their curves from every plot (deleting each plot left with no curve as in LLFR-00051), and clear the undo and redo history.

Note: Creating and deleting a synthetic signal are not undoable actions (LLFR-00140).

*Parent: HLFR-00059*

### LLFR-00263 Removing a synthetic curve keeps the signal
When the user removes the curve of a synthetic signal from a plot (LLFR-00039), or deletes a plot or tab that holds it (LLFR-00049, LLFR-00028), the app must keep the synthetic signal in the signal list. Only "Delete signal" (LLFR-00255) must remove a synthetic signal from the list.

*Parent: HLFR-00059, HLFR-00022*

### LLFR-00265 Rename synthetic signal option
When the user right-clicks a synthetic signal in the signal list panel, the app must show a "Rename" option in the menu of LLFR-00239. The menu of a signal of the data file must not have this option.

*Parent: HLFR-00060*

### LLFR-00266 Rename synthetic signal action
When the user chooses "Rename" (LLFR-00265), the app must let the user type a new name for the synthetic signal, and must then show the new name in the signal list and in the legend of every plot that draws the signal. The names of synthetic signals already computed from it must not change; synthetic signals created from it afterwards must use the new name (LLFR-00240).

Note: Renaming a synthetic signal is not an undoable action (LLFR-00140) and does not clear the undo and redo history.

*Parent: HLFR-00060*

### LLFR-00267 Invalid synthetic signal name
If the user enters a name that, without leading and trailing spaces, is empty or is the name of another signal in the signal list, the app must keep the previous name. For a name already in use, it must show an information box saying that a signal with that name already exists; for an empty name, it must not show any message.

*Parent: HLFR-00060*

### LLFR-00268 Synthetic operation groups
The "Create synthetic signal" option (LLFR-00239) must list the operations in these groups, in this order:
1. Calculus: "Integral", "Derivative";
2. Filters: "Low-pass filter", "High-pass filter", "Moving average";
3. Statistics: "Max", "Min";
4. Comparison: "Greater than", "Less than", "Greater than or equal", "Less than or equal";
5. Arithmetic: "Add constant", "Subtract constant", "Multiply by constant", "Divide by constant", "Product with signal";
6. Spectrum: "FFT".

*Parent: HLFR-00053*

### LLFR-00269 Moving average window dialog
When the user chooses "Moving average", the app must show a dialog that asks for the window size as a whole number of samples and states the allowed range: from 2 up to the number of samples of the signal. The app must create the signal only when the user confirms a value in the allowed range. If the value is outside the range or not a whole number, the dialog must stay open and say why. If the user cancels the dialog, the app must not create any signal.

*Parent: HLFR-00053*

### LLFR-00270 Moving average
The Moving average of a signal must have, at each time sample, the mean of the window of LLFR-00269 centered on that sample, with one more sample after it than before it when the window size is even. Near the first and last samples, the window must hold only the samples that exist.

*Parent: HLFR-00053*

### LLFR-00271 Max and Min
The Max and the Min of a signal must be constant signals, with at every time sample the largest and the smallest value, respectively, of all samples of the signal over the whole time range of the data file, whatever time range the plots show.

*Parent: HLFR-00053*

### LLFR-00272 Constant value dialog
When the user chooses a Comparison or an Arithmetic operation other than "Product with signal" (LLFR-00268), the app must show a dialog that asks for a constant number. The app must create the signal only when the user confirms a number, which must not be 0 for "Divide by constant". If the value is not a number, or is 0 for "Divide by constant", the dialog must stay open and say why. If the user cancels the dialog, the app must not create any signal.

*Parent: HLFR-00053*

### LLFR-00273 Comparison operations
A Comparison signal must have, at each time sample, the value 1 when the signal's sample is greater than ("Greater than"), less than ("Less than"), greater than or equal to ("Greater than or equal") or less than or equal to ("Less than or equal") the constant of LLFR-00272, and the value 0 otherwise.

*Parent: HLFR-00053*

### LLFR-00274 Arithmetic with a constant
An "Add constant", "Subtract constant", "Multiply by constant" or "Divide by constant" signal must have, at each time sample, the signal's sample plus, minus, multiplied by or divided by the constant of LLFR-00272, respectively.

*Parent: HLFR-00053*

### LLFR-00275 Second signal dialog
When the user chooses "Product with signal", the app must show a dialog that lists every signal of the signal list except the FFT signals, including the right-clicked signal, in which the user chooses the second signal. If the user cancels the dialog, the app must not create any signal.

*Parent: HLFR-00053*

### LLFR-00276 Product with signal
The Product of two signals must have, at each time sample, the sample of the right-clicked signal multiplied by the sample of the second signal (LLFR-00275) at the same time sample.

*Parent: HLFR-00053*

### LLFR-00277 Copy name option
When the user right-clicks a signal name in the signal list panel, the app must show a "Copy name" option in the menu of LLFR-00239. When the user chooses it, the app must put the signal's name on the system clipboard as text.

*Parent: HLFR-00061*

### LLFR-00278 Copy equation option
When the user right-clicks a synthetic signal in the signal list panel, the app must show a "Copy equation" option in the menu of LLFR-00239. The menu of a signal of the data file must not have this option.

*Parent: HLFR-00062*

### LLFR-00279 Copy equation action
When the user chooses "Copy equation" (LLFR-00278), the app must put on the system clipboard, as text, the entries that the layout file uses for synthetic signals (LLFR-00225, LLFR-00227) for that synthetic signal and for every synthetic signal it is computed from, directly or through other synthetic signals, in the order they were created, written as a JSON list that can be pasted into the list of synthetic signals of a layout file.

*Parent: HLFR-00062, HLFR-00056*

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

### LLFR-00210 Tab numbers not reused
The app must name each new tab "Tab N", where N grows by 1 for each new tab, and must not reuse the number of a deleted tab, even when the tab's creation is undone. It must also skip every number whose name another tab already has (LLFR-00212). When a file is opened or replaced, numbering must restart with "Tab 1" (LLFR-00016).

*Parent: HLFR-00015*

### LLFR-00212 New tab name not in use
When the app names a new tab (LLFR-00210), it must skip every number N for which another tab is already named "Tab N", so that no two tabs share a name. A skipped number is used up like the number of a deleted tab.

Note: For example, after the user renames "Tab 2" to "Tab 3", the next new tab is named "Tab 4". Names are compared as in LLFR-00211.

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

### LLFR-00042 Hover data tip
While the Data tip button (LLFR-00018) is active and the user hovers over a curve, the app must show a hover data tip with the x-axis and y-axis values of the hovered point.

*Parent: HLFR-00024*

### LLFR-00043 Data tip x value
The data tip must show the x-axis value in seconds.

*Parent: HLFR-00024, HLFR-00007*

### LLFR-00044 Data tip y value
The data tip must show the y-axis value as stored in the file, without a unit.

*Parent: HLFR-00024*

### LLFR-00045 Pin a data tip
If the user left-clicks a curve while the hover data tip (LLFR-00042) is shown, the app must fix the data tip at that point in the plot.

*Parent: HLFR-00025*

### LLFR-00046 Pinned data tip menu
When the user right-clicks a pinned data tip, the app must show a menu with a "Delete" option.

*Parent: HLFR-00025*

### LLFR-00047 Remove a pinned data tip
When the user chooses "Delete" in the pinned data tip menu (LLFR-00046), the app must remove the pinned data tip from the plot.

*Parent: HLFR-00025*

### LLFR-00048 Plot menu delete option
When the user right-clicks an empty area of a plot (not on a curve, a pinned data tip, a vertical marker or a delta marker), the app must show a menu with a "Delete plot" option.

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

### LLFR-00211 Unique tab name on rename
If the user enters a tab name (LLFR-00030) that, without leading and trailing spaces, is the name of another tab, the app must keep the tab's previous name and must show an information box saying that a tab with that name already exists. Names must be compared exactly, so that names that differ only in uppercase and lowercase letters are different names. Entering the tab's own current name is not a conflict.

Note: The app stores a tab name without its leading and trailing spaces. The information box is not an error box (HLFR-00002), like the Full Tab Notification box (LLFR-00032). A rejected rename changes nothing, so it is not an undoable action (LLFR-00140).

*Parent: HLFR-00017*

### LLFR-00068 Time on the x-axis
Every time plot (HLFR-00058) must use the time signal (HLFR-00006) as its x-axis.

*Parent: HLFR-00012, HLFR-00013, HLFR-00007*

### LLFR-00069 Vertical stacking of plots
The plots in a tab must be stacked vertically, one below the other.

*Parent: HLFR-00014, HLFR-00018*

### LLFR-00070 Shared time axis
All time plots in all tabs must share the same x-axis range, so that a change to the time range of one time plot applies to every time plot in every tab.

*Parent: HLFR-00014, HLFR-00027, HLFR-00036*

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
While the Zoom button (LLFR-00077) is active and the user left-clicks a plot and releases the button less than 5 pixels from where it was pressed (LLFR-00208), the app must narrow the plot's x-axis range to 95% of its width, centered on the time of the clicked point.

*Parent: HLFR-00027*

### LLFR-00081 Place a marker by click
While the Vertical marker button (LLFR-00080) is active and the user left-clicks a plot anywhere other than on an existing vertical marker, the app must draw a new vertical marker at the time of the clicked point on every plot (LLFR-00205).

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
The app must name each new vertical marker "Marker N", where N is 1 for the first marker placed after a file is opened and grows by 1 for each new marker.

Note: Vertical markers are shared by all plots (LLFR-00205), so the numbering is shared too, and it restarts when a file is opened or replaced (LLFR-00013).

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
When the user chooses "Delete" in the marker menu (LLFR-00090), the app must remove that marker and its label from every plot.

*Parent: HLFR-00031*

### LLFR-00092 Marker time value
The app must show the time of a vertical marker, in seconds, directly below the marker's label (LLFR-00084).

*Parent: HLFR-00028, HLFR-00007*

### LLFR-00093 Marker time value while dragging
While the user drags a vertical marker (LLFR-00086), the app must update the marker's time value (LLFR-00092) to the marker's current position.

*Parent: HLFR-00029*

### LLFR-00203 Marker preview
While the Vertical marker button (LLFR-00080) is active, including while the Shift key is held (LLFR-00154), and the mouse pointer is over a plot's drawing area but not over an existing vertical marker, the app must show a preview of the marker that a click would place on every time plot of the current tab: a dashed vertical line at the time under the pointer, in a paler version of the marker color (LLFR-00083), with its time value (LLFR-00092). The app must hide the preview when the pointer leaves the plot's drawing area, moves over an existing vertical marker, or the button is deactivated. The preview must not appear in the PDF export (LLFR-00129) or the copied image (LLFR-00133).

Note: Plots in tabs that are not shown don't need the preview.

*Parent: HLFR-00028*

### LLFR-00205 Markers on every plot
Every vertical marker must be shown on every time plot in every tab, including time plots created after the marker. Moving (LLFR-00086), renaming (LLFR-00088) or deleting (LLFR-00091) a marker on any time plot must apply to it on every time plot; while a marker is dragged, it must follow the pointer on every time plot of the current tab, and on the time plots of the other tabs it must be at its new time at the latest when the button is released. When no plot is left in any tab, whether because a plot is deleted (LLFR-00049, LLFR-00051), a tab is deleted (LLFR-00028) or the file is replaced (LLFR-00015), the app must delete every vertical marker. When the cause is deleting a plot or a tab, the markers must be deleted as part of that same action, so that undoing it (LLFR-00138) brings the markers back.

Note: Each of these remains one undoable action (LLFR-00140).

*Parent: HLFR-00028, HLFR-00029, HLFR-00030, HLFR-00031*

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
The app must not reuse the number of a deleted vertical marker (LLFR-00085) for a new marker, even when the marker's placement is undone, until a file is opened or replaced.

*Parent: HLFR-00028*

### LLFR-00112 Renamed marker label
After the user types a new marker name (LLFR-00088), the app must show the new name in the marker's label (LLFR-00084).

*Parent: HLFR-00030*

### LLFR-00113 Wheel zoom step
Each notch of the mouse wheel (15 degrees of rotation) must change the x-axis range of the plot by 5%: turning forward must narrow the range to 95% of its width, and turning backward must widen it to 1/0.95 of its width. Smaller wheel movements, such as from a touchpad, must zoom in proportion.

*Parent: HLFR-00027*

### LLFR-00206 Wheel direction on a trackpad
On macOS, the app must zoom in when the user's fingers move up on the trackpad and zoom out when they move down, as with the mouse wheel turning forward and backward (LLFR-00074), whatever the system's "natural scrolling" setting.

*Parent: HLFR-00027*

### LLFR-00208 Time span selection
While the Zoom button (LLFR-00077) is active and the user presses the left mouse button on a plot and moves the pointer 5 pixels or more from where the button was pressed, the app must show a horizontal dashed line at the height of the press, from the time of the press to the time under the pointer, with a short vertical line at each end, in the reserved marker color (LLFR-00083, LLFR-00172).

*Parent: HLFR-00027*

### LLFR-00209 Zoom to the selected span
When the user releases the left mouse button after LLFR-00208, the app must remove the selection line and set the plot's x-axis range to the selected time span, so that its two ends are the plot's left and right edges, applied to every plot (LLFR-00070), with the y-axis ranges set as in LLFR-00076. If the button is released outside the plot's drawing area, the end of the span must be the time at the nearer left or right edge of the drawing area. The span must be limited to the file's time range (LLFR-00119).

Note: A release less than 5 pixels from the press is a click (LLFR-00078).

*Parent: HLFR-00027*

### LLFR-00115 Reset zoom action
When the user clicks the Reset zoom button (LLFR-00114), the app must set the x-axis range of every time plot in every tab to the whole time range of the file, and must set their y-axis ranges as in LLFR-00076. Frequency plots are reset as in LLFR-00258.

*Parent: HLFR-00035*

### LLFR-00117 Pan by wheel drag
When the user holds the mouse wheel pressed over a plot and moves the mouse left or right, the app must shift the plot's x-axis range so that the curves follow the mouse pointer horizontally, whether or not a plot tool is active.

*Parent: HLFR-00036*

### LLFR-00118 No pan without zoom
While a plot shows the whole time range of the file, holding the mouse wheel pressed and moving the mouse must not change the plot's x-axis range.

*Parent: HLFR-00036*

### LLFR-00119 Pan limits
The app must not pan a plot's x-axis range before the first time sample or after the last time sample of the file.

*Parent: HLFR-00036*

### LLFR-00120 Curves visible after pan
After every pan, the app must set the y-axis range of each plot as in LLFR-00076.

*Parent: HLFR-00036*

### LLFR-00122 Show the grid
When the user clicks the Grid button (LLFR-00121) while the grid is hidden, the app must show a grid on every plot in every tab.

*Parent: HLFR-00037*

### LLFR-00123 Hide the grid
When the user clicks the Grid button (LLFR-00121) while the grid is shown, the app must hide the grid on every plot in every tab.

*Parent: HLFR-00037*

### LLFR-00125 Grid on new plots
While the grid is shown, every new plot must also show the grid.

*Parent: HLFR-00037*

### LLFR-00143 Dashed marker line
The app must draw the line of a vertical marker as a dashed line.

*Parent: HLFR-00028*

### LLFR-00144 First three curve colors
The first three colors of the palette of LLFR-00033 must be blue, black and red, in that order, so that the first curve drawn in a plot is blue, the second black and the third red.

*Parent: HLFR-00020*

### LLFR-00147 Grid hidden at start
When the app starts, the grid must be hidden.

*Parent: HLFR-00037*

### LLFR-00151 Data tip leader line
The app must connect each pinned data tip (LLFR-00045) to the point whose values it shows with a dashed line.

*Parent: HLFR-00025*

### LLFR-00152 Drag a pinned data tip
When the user presses the left mouse button on a pinned data tip and drags it, the app must move the data tip with the mouse pointer and leave it where the button is released, while the data tip keeps showing the values of the same point.

*Parent: HLFR-00041*

### LLFR-00153 Press on a pinned data tip
A left mouse button press on a pinned data tip must start moving it (LLFR-00152), whether or not a plot tool is active, and must not pin a new data tip, zoom, place a vertical marker or pick a delta marker point.

*Parent: HLFR-00041, HLFR-00032*

### LLFR-00163 Pick the first point
While the Delta X button (LLFR-00161) or the Delta Y button (LLFR-00162) is active and the user left-clicks a curve, the app must take the curve sample nearest to the mouse pointer as the first point of a measurement and mark it in the plot with a dot.

*Parent: HLFR-00043, HLFR-00044*

### LLFR-00164 Pick the second point
When the user then left-clicks a curve in the same plot, the app must take the curve sample nearest to the mouse pointer as the second point, remove the dot of LLFR-00163 and draw a Delta X marker (LLFR-00168) or a Delta Y marker (LLFR-00170) between the two points, according to the active button. The two points may be on the same curve or on different curves.

*Parent: HLFR-00043, HLFR-00044*

### LLFR-00165 Click outside a curve
While a first point is picked (LLFR-00163), a left-click that is not on a curve must keep the first point and must not show any message.

*Parent: HLFR-00043, HLFR-00044*

### LLFR-00166 First point in another plot
While a first point is picked (LLFR-00163), a left-click on a curve in another plot must discard the first point and its dot and take the clicked sample as the new first point (LLFR-00163).

*Parent: HLFR-00043, HLFR-00044*

### LLFR-00167 First point discarded
When the Delta X or Delta Y button is deactivated while a first point is picked (LLFR-00163), the app must discard the first point and remove its dot.

*Parent: HLFR-00043, HLFR-00044*

### LLFR-00168 Delta X marker
A Delta X marker must mark its two points with dots and draw a dashed horizontal curly bracket whose two ends are at the times of the two points, placed just above the higher of the two points, with its middle point pointing up, away from the points.

Note: The curly bracket gives delta markers a visual identity of their own, different from the straight dashed line of a vertical marker (LLFR-00143), although both use the same color (LLFR-00172).

*Parent: HLFR-00043*

### LLFR-00169 Delta X value
A Delta X marker must show the text "Δt = <value> s" next to the middle point of its curly bracket, where the value is the time of the second point minus the time of the first point, in seconds, in the same number format as the data tip's x value (LLFR-00043).

*Parent: HLFR-00043, HLFR-00007*

### LLFR-00170 Delta Y marker
A Delta Y marker must mark its two points with dots and draw a dashed vertical curly bracket whose two ends are at the y-axis values of the two points, placed just to the right of the later of the two points, with its middle point pointing right, away from the points. When the bracket and its value (LLFR-00171) do not fit to the right of the later point inside the plot's drawing area, the app must draw them mirrored, just to the left of the earlier of the two points, with the middle point pointing left.

Note: If neither side has room for the bracket and its value, the app uses the side with more room. The bracket is cut at the edge of the plot only when one of its points is itself outside the shown x-axis range, or when the two points leave less room than the bracket needs on both sides.

*Parent: HLFR-00044*

### LLFR-00171 Delta Y value
A Delta Y marker must show the text "Δy = <value>" next to the middle point of its curly bracket, where the value is the y-axis value of the second point minus the y-axis value of the first point, without a unit, in the same number format as the data tip's y value (LLFR-00044).

*Parent: HLFR-00044*

### LLFR-00172 Delta marker color
The app must draw delta markers and the dot of LLFR-00163 in the reserved marker color of vertical markers (LLFR-00083), which it never uses for curves (LLFR-00033, LLFR-00034).

*Parent: HLFR-00043, HLFR-00044, HLFR-00020*

### LLFR-00173 Delta marker follows its points
A delta marker must stay attached to its two points, and its value must stay unchanged, when the plot's x-axis or y-axis range or the plot's size changes.

*Parent: HLFR-00043, HLFR-00044*

### LLFR-00174 Several delta markers
A plot must be able to hold any number of Delta X and Delta Y markers at the same time.

*Parent: HLFR-00043, HLFR-00044*

### LLFR-00175 Delta marker menu
When the user right-clicks a delta marker, the app must show a menu with a "Delete" option.

*Parent: HLFR-00043, HLFR-00044*

### LLFR-00176 Delete delta marker action
When the user chooses "Delete" in the delta marker menu (LLFR-00175), the app must remove that delta marker from the plot.

*Parent: HLFR-00043, HLFR-00044*

### LLFR-00177 Delta marker menu over a curve
When the user right-clicks a point where a delta marker overlaps a curve, the app must show the delta marker menu (LLFR-00175) and not the curve menu (LLFR-00038, LLFR-00040).

*Parent: HLFR-00043, HLFR-00044*

### LLFR-00178 Delta markers of a removed curve
When a curve is removed from a plot (LLFR-00039), the app must also remove every delta marker that has a point on that curve.

*Parent: HLFR-00043, HLFR-00044, HLFR-00022*

### LLFR-00179 Pinned data tip kept inside the plot
Whenever a plot changes size or x-axis or y-axis range (for example when plots are added to or deleted from its tab, when the window or the panels are resized, or after a zoom or a pan), and when a data tip drag ends (LLFR-00152), the app must draw each pinned data tip whose point is within the shown range at the position the user gave it (LLFR-00045, LLFR-00152), moved by the shortest distance needed to keep the whole data tip inside the plot's drawing area, still connected to its point by its leader line (LLFR-00151).

Note: When the plot grows again, the data tip returns towards the position the user gave it.

*Parent: HLFR-00025, HLFR-00041*

### LLFR-00180 Time range of a new plot
A new time plot must show the x-axis range shared by the existing time plots (LLFR-00070), or the whole time range of the file when no other time plot exists.

*Parent: HLFR-00012, HLFR-00014*

### LLFR-00256 Frequency plot
When the user double-clicks an FFT signal (LLFR-00019), the app must create a frequency plot in the current tab, with frequency in Hz on its x-axis, labeled "Frequency (Hz)", and draw the FFT signal in it. A frequency plot counts towards the maximum number of plots of a tab (HLFR-00018).

*Parent: HLFR-00058*

### LLFR-00257 FFT and time signals in separate plots
If the user drops an FFT signal on a time plot, or any other signal on a frequency plot, the app must not draw the signal and must show an information box saying that FFT signals and time signals cannot be drawn in the same plot.

*Parent: HLFR-00058, HLFR-00013*

### LLFR-00258 Frequency plot x-axis range
Each frequency plot must have its own x-axis range, which must not follow the time plots (LLFR-00070) or the other frequency plots. A new frequency plot must show the frequencies from 0 Hz up to the highest frequency of its curves. Mouse wheel zoom (LLFR-00074), click zoom (LLFR-00078), span zoom (LLFR-00209) and pan (LLFR-00117) must change only the frequency plot they are used on, limited to that frequency range, and Reset zoom (LLFR-00115) must return every frequency plot to that frequency range.

*Parent: HLFR-00058, HLFR-00027, HLFR-00035, HLFR-00036*

### LLFR-00259 No vertical markers on frequency plots
The app must not show vertical markers or their preview (LLFR-00203, LLFR-00205) on frequency plots, and a click on a frequency plot while the Vertical marker button is active must not place a marker.

*Parent: HLFR-00058, HLFR-00028*

### LLFR-00260 Data tip on a frequency plot
A data tip on a frequency plot must show the x-axis value in Hz, instead of seconds (LLFR-00043).

*Parent: HLFR-00058, HLFR-00024*

### LLFR-00261 Delta X on a frequency plot
A Delta X marker on a frequency plot must show the text "Δf = <value> Hz", where the value is the frequency of the second point minus the frequency of the first point, instead of the text of LLFR-00169.

*Parent: HLFR-00058, HLFR-00043*
