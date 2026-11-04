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

### LLFR-00058 Top panel position
The top panel must be placed above the other two panels.

*Parent: HLFR-00001*

### LLFR-00440 Signal list panel position
The signal list panel must be placed to the right of the plot panel.

*Parent: HLFR-00001*

### LLFR-00071 Unexpected error box
If an unexpected error occurs while the app handles a user action, the app must show an error box titled "Error" that describes the error, except as in LLFR-00968.

*Parent: HLFR-00002*

### LLFR-00441 Keep running after an unexpected error
If an unexpected error occurs while the app handles a user action, the app must keep running.

*Parent: HLFR-00002*

### LLFR-00072 Initial signal list width
When the app starts, the signal list panel must take 20% of the app window's width.

*Parent: HLFR-00001, HLFR-00026*

### LLFR-00442 Initial plot panel width
When the app starts, the plot panel must take the rest of the width left by the signal list panel (LLFR-00072), 80%.

*Parent: HLFR-00001, HLFR-00026*

### LLFR-00073 Drag to resize the panels
The user must be able to drag the border between the plot panel and the signal list panel to change their widths.

*Parent: HLFR-00026*

### LLFR-00280 Resize border highlight
While the mouse pointer is over the part of the border between the plot panel and the signal list panel where a drag changes their widths (LLFR-00073), and while the user drags that border, the app must draw a blue vertical line, 2 pixels wide, along the border over the full height of the two panels.

*Parent: HLFR-00026*

### LLFR-00443 Resize border highlight hidden
The app must hide the line of LLFR-00280 as soon as the pointer is no longer over the part of the border of LLFR-00280 and no drag is in progress.

Note: The line is hidden the rest of the time, so the border is visible only when the user can use it.

*Parent: HLFR-00026*

### LLFR-00281 Resize pointer
While the mouse pointer is over the part of the border of LLFR-00280, and while the user drags it, the app must show the mouse pointer as a horizontal resize pointer.

*Parent: HLFR-00026*

### LLFR-00138 Undo action
When the user clicks the Undo button (LLFR-00136) or presses its shortcut (LLFR-00137), the app must reverse the most recent undoable action (LLFR-00140) that has not been undone yet, returning the tabs, plots, curves, data tips, flags, delta markers, areas, text notes and arrows to the state they were in before that action.

*Parent: HLFR-00040*

### LLFR-00139 Undo depth
The app must keep only the 30 most recent undoable actions for undo, so that the user can undo at most 30 actions in a row.

*Parent: HLFR-00040*

### LLFR-00140 Undoable actions
The app must treat these actions as undoable: adding a tab, deleting a tab, renaming a tab, creating a plot, deleting a plot, adding a curve to a plot, removing a curve from a plot, changing a curve's width, pinning a data tip, moving a pinned data tip, deleting a pinned data tip, placing a flag, moving a flag, renaming a flag, changing a flag's color, deleting a flag, placing a delta marker, renaming a delta marker, moving a point of a delta marker, changing a delta marker's color, deleting a delta marker, creating an area, moving or resizing an area, renaming an area, changing an area's color, deleting an area, creating a text note, moving a text note, editing a text note, changing a text note's size, border color or text color, deleting a text note, drawing an arrow, moving an arrow, rotating or stretching an arrow, renaming an arrow, changing an arrow's color, deleting an arrow, and each of the deletions of LLFR-00412 to LLFR-00417 (all the pinned data tips of a plot or of all plots, all the delta markers of a plot or of all plots, all the flags, all the areas).

Note: Removing a curve also removes its delta markers (LLFR-00178), and undoing the removal brings them back. Opening a file, closing a file or all files (LLFR-00919, LLFR-00929), zooming, panning, resetting the zoom, showing or hiding the grid, exporting, copying, searching and resizing the panels are not undoable. Saving and loading a layout (LLFR-00494) and saving the signals (LLFR-00556) are not undoable either. Creating and deleting a synthetic signal (LLFR-00255) are not undoable either. Activating or deactivating a plot tool, including with the Esc key (LLFR-00370), is not undoable either. Cancelling the color picker, or confirming or choosing from the recent colors (LLFR-00419) the color an item already has, is not an undoable action (LLFR-00812).

*Parent: HLFR-00040*

### LLFR-00142 Undo history kept on file open
When the app opens a data file, it must keep the undo history and the redo history (LLFR-00192) unchanged.

Note: Closing a data file clears them (LLFR-00925).

*Parent: HLFR-00040, HLFR-00048, HLFR-00117*

### LLFR-00192 Redo action
When the user clicks the Redo button (LLFR-00190) or presses its shortcut (LLFR-00191), the app must reapply the most recently undone action (LLFR-00138) that has not been redone yet, returning the tabs, plots, curves, data tips, flags, delta markers, areas, text notes and arrows to the state they were in after that action.

Note: The user can redo, one by one, every action undone since the last new undoable action, so at most 30 (LLFR-00139).

*Parent: HLFR-00048*

### LLFR-00444 Redone action can be undone again
When the app reapplies an action as in LLFR-00192, it must make that action available to undo again.

*Parent: HLFR-00048*

### LLFR-00193 New action clears redo
When the user does an undoable action (LLFR-00140) after undoing, the app must discard all undone actions, so that they can no longer be redone.

*Parent: HLFR-00048*

### LLFR-00195 Redo shortcut while typing
While the keyboard focus is in a text field (LLFR-00157), the Redo shortcut (LLFR-00191) must not redo actions on the tabs, plots, curves, data tips, flags, delta markers, areas, text notes and arrows.

Note: This lets Ctrl+Y act on the text being typed, as text fields usually do.

*Parent: HLFR-00048*

### LLFR-00196 Undo shortcut while typing
While the keyboard focus is in a text field (LLFR-00157), the Undo shortcut (LLFR-00137) must not undo actions on the tabs, plots, curves, data tips, flags, delta markers, areas, text notes and arrows.

Note: This lets Ctrl+Z (Cmd+Z on macOS) act on the text being typed, as text fields usually do.

*Parent: HLFR-00040*

### LLFR-00182 Where the app icon is shown
The app must show its icon (HLFR-00045), instead of the default PyInstaller or Python icon, as the icon of the standalone executable (COR-00007), in the list of open apps (the Dock and the app switcher on macOS, the taskbar on Windows), and in the main window's title bar where the operating system shows an icon there.

*Parent: HLFR-00045*

### LLFR-00183 App icon picture
The app icon must show a small line chart with a blue curve and a red curve (LLFR-00144) over a pair of axes, on a light rounded square.

*Parent: HLFR-00045*

### LLFR-00445 App icon at small size
The app icon (LLFR-00183) must stay recognizable at 16 by 16 pixels.

*Parent: HLFR-00045*

### LLFR-00184 Splash screen at launch
When the user launches the app, the app must show the splash screen (HLFR-00046) within 2 seconds, before the main window is ready.

Note: The limit is checked against the median time over the launches from the second one onward, on the computer the app is tested on. The time of the first launch is measured and reported, but it is not checked against the limit.

*Parent: HLFR-00046*

### LLFR-00185 Splash screen content
The splash screen must show the app icon (LLFR-00183), the app name "plot_tool" and the text "Loading...".

*Parent: HLFR-00046, HLFR-00045*

### LLFR-00186 Splash screen closes
The app must close the splash screen at the moment the main window becomes visible, so that the splash screen is never shown above the main window.

*Parent: HLFR-00046*

### LLFR-00187 Splash screen on a startup error
If an error stops the app from starting, the app must close the splash screen before it shows the error box (HLFR-00002).

*Parent: HLFR-00046, HLFR-00002*

### LLFR-00188 Opening time limit
The standalone executable (COR-00007) must show the main window, ready to respond to the user, at most 5 seconds after the user launches it.

Note: The time is measured from the second launch onward, on the computer the app is tested on, so that work done only once on the first launch does not count.

*Parent: HLFR-00047*

### LLFR-00189 No repeated startup work
The app must only repeat on each launch the startup work whose results can change between launches.

Note: For example, the cache of fonts used to draw text in the plots is built on the first launch and reused on later launches.

*Parent: HLFR-00047*

### LLFR-00406 Dialog opening time limit
The file selection dialog of the Open file button (LLFR-00005), the dialogs of the Save layout and Load layout buttons (LLFR-00219, LLFR-00221), the save file dialog of "Save all tabs as PDF" (LLFR-00128) and the save file dialog of the Save signals button (LLFR-00396) must each appear at most 0.65 seconds after the user's click, including the first click after the app starts.

Note: As in LLFR-00188, the time is measured from the second launch onward, on the computer the app is tested on, so that work done only once on the first launch does not count. The limit is checked against the median time of each dialog over the launches from the second one onward.

*Parent: HLFR-00091*


## Top panel

### LLFR-00004 Open file button
The top panel must contain a button called "Open file".

*Parent: HLFR-00004*

### LLFR-00005 File selection dialog
When the user clicks the open file button (LLFR-00004), the app must show a file selection dialog, except as in LLFR-00891.

*Parent: HLFR-00004*

### LLFR-00946 Several files in the file dialog
The file selection dialog of LLFR-00005 must let the user select several files at once.

*Parent: HLFR-00122, HLFR-00004*

### LLFR-00947 Order of the selected files
When the user selects several files in the dialog of LLFR-00005, the app must take them one after the other, in character order of their file names without their folders, ignoring the difference between uppercase and lowercase letters, so that the files that open get their numbers (LLFR-00895) in that order.

Note: The order compares characters, not numbers, so `run10.csv` comes before `run2.csv`. Two names that differ only in uppercase and lowercase letters are taken in the order of an exact comparison.

*Parent: HLFR-00122, HLFR-00114*

### LLFR-00948 Next selected file after a file that does not open
When a selected file fails to open (LLFR-00510, LLFR-00968), is refused (LLFR-00893, LLFR-00949) or its time signal window is cancelled (LLFR-00327), the app must go on with the next selected file of LLFR-00947.

Note: A cancelled time signal window therefore cancels only that file, with no message (LLFR-00509).

*Parent: HLFR-00122, HLFR-00101*

### LLFR-00949 Selected files beyond 10 open files
When 10 data files are open while selected files of LLFR-00947 are still left to open, the app must refuse each of those files, listing it in the information box of LLFR-00951 as not opened because 10 files are already open.

*Parent: HLFR-00122, HLFR-00113*

### LLFR-00950 One File Open Error box for a selection
After the app has taken all the selected files (LLFR-00947), if any of them could not be opened at the reading step of LLFR-00328 or met an unexpected error (LLFR-00968), the app must show one File Open Error box that lists each such file by its name, without its folder, with the reason of its error (LLFR-00008, LLFR-00009, LLFR-00011, LLFR-00012, LLFR-00064, LLFR-00065, LLFR-00968).

Note: With one file selected, the box lists that one file. The File Open Error box that LLFR-00008, LLFR-00009, LLFR-00011, LLFR-00012, LLFR-00064 and LLFR-00065 name is this one box; the text each one gives is the reason listed for that file.

*Parent: HLFR-00122, HLFR-00002, HLFR-00004*

### LLFR-00951 One information box for the refused files
After the app has taken all the selected files (LLFR-00947), and after the box of LLFR-00950 when that box is shown, if any selected file was refused (LLFR-00893, LLFR-00949), the app must show one information box that lists each refused file by its name, without its folder, with the reason of LLFR-00893 or LLFR-00949.

Note: The box is an information box, not an error box (HLFR-00002), like the Full Tab Notification box (LLFR-00032).

*Parent: HLFR-00122, HLFR-00113*

### LLFR-00968 Unexpected error while opening one of the selected files
If an unexpected error (LLFR-00071) occurs while the app takes one selected file (LLFR-00328), the app must treat it as a reading error of that file, listing the file in the box of LLFR-00950 with a description of the error as its reason.

Note: The app then goes on with the next selected file (LLFR-00948).

*Parent: HLFR-00122, HLFR-00002*

### LLFR-00204 File dialog starting folder
The first time the user clicks the Open file button after the app starts, the file selection dialog (LLFR-00005) must show the folder that contains the standalone executable (COR-00007): the folder that holds `plot_tool.app` on macOS, or the folder that holds the executable on Windows, except as in LLFR-00446.

*Parent: HLFR-00004*

### LLFR-00446 File dialog starting folder from source
When the app runs from source, the first time the user clicks the Open file button after the app starts, the file selection dialog (LLFR-00005) must show the repository folder.

*Parent: HLFR-00004*

### LLFR-00447 File dialog folder of the last opened file
After the first time the user clicks the Open file button after the app starts (LLFR-00204, LLFR-00446), the file selection dialog (LLFR-00005) must show the folder of the last file the app opened successfully.

*Parent: HLFR-00004*

### LLFR-00006 Open the selected file
When the user selects one or more files in the file selection dialog (LLFR-00005, LLFR-00946), the app must try to open each selected file in the steps of LLFR-00328, one file after the other in the order of LLFR-00947.

*Parent: HLFR-00004, HLFR-00122*

### LLFR-00890 Maximum of open data files
The app must allow up to 10 data files to be open at the same time.

*Parent: HLFR-00113*

### LLFR-00891 Open file with 10 files open
When the user clicks the Open file button (LLFR-00004) while 10 data files are open, the app must show, in place of the file selection dialog (LLFR-00005), an information box saying that 10 files are already open and that closing one of them makes room for another.

Note: The box is an information box, not an error box (HLFR-00002), like the Full Tab Notification box (LLFR-00032).

*Parent: HLFR-00113, HLFR-00004*

### LLFR-00892 Open files kept with 10 files open
When the user clicks the Open file button while 10 data files are open (LLFR-00891), the app must keep the open data files, the plots and the undo and redo history unchanged.

*Parent: HLFR-00113*

### LLFR-00893 File already open
When a file selected in the file selection dialog (LLFR-00005) is already open as data file N, the app must refuse it, listing it in the information box of LLFR-00951 as already open as `file<N>`.

Note: Two paths name the same file when they lead to the same file on disk, for example through a symbolic link. The check is step 2 of LLFR-00328, after the 10-file limit of step 1 and before the file is read. When both refusals apply, the file is refused for the 10-file limit (LLFR-00949).

*Parent: HLFR-00113, HLFR-00004*

### LLFR-00894 Open files kept when the file is already open
When the app refuses a selected file because it is already open (LLFR-00893), it must keep the open data files unchanged, as in LLFR-00010.

*Parent: HLFR-00113, HLFR-00101*

### LLFR-00895 File number
When the app opens a data file, it must give it the number that is 1 more than the highest number given to a data file since the app started, or 1 for the first data file opened since the app started.

*Parent: HLFR-00114*

### LLFR-00896 File number kept while open
A data file must keep its number (LLFR-00895) for as long as it stays open, whatever other data files are opened or closed.

*Parent: HLFR-00114*

### LLFR-00897 Numbers of closed files used up
The app must keep the number of each closed data file used up until the app closes, so that no later data file gets it.

Note: After file 2 of three open files is closed, file 3 keeps the number 3, and the next file opened is file 4.

*Parent: HLFR-00114*

### LLFR-00898 Number only for an opened file
The app must give a number (LLFR-00895) only to a file it opens, so that a file whose opening fails, is cancelled or is refused (LLFR-00010, LLFR-00891, LLFR-00893, LLFR-00949) uses up no number.

*Parent: HLFR-00114*

### LLFR-00899 Numbering after Close all files
After "Close all files" (LLFR-00931), the app must give the next data file opened the next number of LLFR-00895, so that numbering restarts at 1 only when the app starts.

*Parent: HLFR-00114, HLFR-00119*

### LLFR-00915 Opening adds the file
When the app opens a selected file (LLFR-00328, step 5), it must add it as the next data file (LLFR-00895), whether or not other data files are open.

*Parent: HLFR-00117, HLFR-00113*

### LLFR-00916 Open files kept when a file is added
When the app adds a data file (LLFR-00915), it must keep the data files already open unchanged, with their numbers, signals, synthetic signals, tabs, plots, curves, pinned data tips, flags, delta markers, areas, text notes and arrows.

*Parent: HLFR-00117*

### LLFR-00917 Added file read without a question
When the user selects a file while other data files are open, the app must go on to the reading step of LLFR-00328 right away, with no question to the user.

*Parent: HLFR-00117*

### LLFR-00007 Cancel file selection
If the user cancels the file selection dialog (LLFR-00005), the app must keep the open data files and the signal list unchanged.

*Parent: HLFR-00004*

### LLFR-00008 Unreadable file
If the file cannot be read or parsed (for example, it is corrupt or its content does not match its format), the app must show the File Open Error box saying that the file could not be read.

*Parent: HLFR-00004, HLFR-00002*

### LLFR-00009 File access error
If the file does not exist or the app has no permission to read it, the app must show the File Open Error box saying that the file could not be accessed.

*Parent: HLFR-00004, HLFR-00002*

### LLFR-00010 State after a failed open
When opening a selected file fails, is cancelled after the user selected it, or is refused (LLFR-00891, LLFR-00893, LLFR-00949), the app must make no change for that file to the open data files, the tabs and plots, the signal list, the synthetic signals or the undo and redo history.

*Parent: HLFR-00004, HLFR-00101*

### LLFR-00011 Unsupported file format
If the user selects a file whose format is not listed in HLFR-00005, the app must show the File Open Error box saying that the file format is not supported.

*Parent: HLFR-00005, HLFR-00002*

### LLFR-00012 Failed content check message
If the file fails the check in HLFR-00008 or HLFR-00009, the app must show the File Open Error box saying that the file cannot be opened and which check failed.

*Parent: HLFR-00008, HLFR-00009, HLFR-00002*

### LLFR-00013 DELETED
DELETED

### LLFR-00448 DELETED
DELETED

### LLFR-00014 DELETED
DELETED

### LLFR-00449 DELETED
DELETED

### LLFR-00450 DELETED
DELETED

### LLFR-00015 DELETED
DELETED

### LLFR-00016 DELETED
DELETED

### LLFR-00017 DELETED
DELETED

### LLFR-00018 Data tip button
The top panel must contain a button called "Data tip".

*Parent: HLFR-00024, HLFR-00032*

### LLFR-00053 Case-insensitive time signal name
The app must match the time signal name `Time` (HLFR-00006) ignoring the difference between uppercase and lowercase letters, so that a signal named `time` or `TIME` is the time signal.

*Parent: HLFR-00006*

### LLFR-00059 CSV and Excel layout
In CSV and Excel files, the app must read each column as one signal and each row below the first as one sample.

*Parent: HLFR-00005*

### LLFR-00451 CSV and Excel signal names
In CSV and Excel files, the app must take the signal names from the first row.

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
In MAT files, the app must ignore top-level variables that do not hold a one-dimensional numeric array.

*Parent: HLFR-00005*

### LLFR-00452 Checks on the MAT signals read
In MAT files, the app must apply the checks of HLFR-00008 and HLFR-00009 only to the signals it read (LLFR-00062).

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

### LLFR-00080 Flag button
The top panel must contain a button called "Flag".

*Parent: HLFR-00028, HLFR-00032*

### LLFR-00109 Plot tools stay active
A plot tool button must stay active after its tool is used, until the user clicks the button again (LLFR-00002) or activates another plot tool (LLFR-00079).

Note: For a plot tool, the function of LLFR-00003 finishes only when the tool is deactivated, not after each zoom, pin or placed flag.

*Parent: HLFR-00032, HLFR-00003*

### LLFR-00114 Reset zoom button
The top panel must contain a button called "Reset zoom".

*Parent: HLFR-00035*

### LLFR-00116 Reset zoom button feedback
When the user clicks the Reset zoom button, the button must show its active color (LLFR-00001) until the zoom reset (LLFR-00115, LLFR-00677) has finished, and for at least 0.3 seconds.

*Parent: HLFR-00035, HLFR-00003*

### LLFR-00453 Reset zoom button back to normal
After the Reset zoom button has shown its active color as in LLFR-00116, the button must return to its normal color (LLFR-00003).

*Parent: HLFR-00035, HLFR-00003*

### LLFR-00207 Z key resets the zoom
When the user presses the Z key alone, with no other keyboard key, the app must reset the zoom as if the Reset zoom button were clicked (LLFR-00115, LLFR-00677, LLFR-00116, LLFR-00453), except as in LLFR-00454.

Note: Ctrl+Z and Cmd+Z stay Undo (LLFR-00137).

*Parent: HLFR-00035*

### LLFR-00454 Z key while dragging
While the user is dragging the mouse (a pan, a flag, area, text note, data tip, arrow or delta marker point drag, the drawing of an area or an arrow, or a time span selection), the Z key must do nothing.

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
The saved PDF must have one page for each tab that holds at least one plot, in tab order, with the tab's name at the top of the page, the description of the data files of LLFR-00966 directly below it, and the tab's plots below the description as they are shown on screen, including their time range, curves, legends, grid, flags, areas, text notes, arrows, delta markers and pinned data tips.

*Parent: HLFR-00038, HLFR-00113*

### LLFR-00966 Data files described on each PDF page
On each page of the PDF (LLFR-00129), directly below the tab's name, the app must show a description of all the open data files, as `file<N> = <file name>` for each of them, with the file name with its extension and without its folder, separated by commas, in the order of the file numbers, for example `file1 = run_A.csv, file2 = run_B.mat`.

*Parent: HLFR-00038, HLFR-00113*

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
When the user clicks the Copy button, the app must put on the system clipboard an image of all plots of the current tab as they are shown on screen, including their flags, areas, text notes, arrows, delta markers and pinned data tips, without any preview, with the strip of LLFR-00967 above the plots.

*Parent: HLFR-00039, HLFR-00113*

### LLFR-00967 Data files described on the copied image
The image that the Copy button puts on the clipboard (LLFR-00133) must have at its top, above the plots, its own strip with the description of all the open data files of LLFR-00966, so that the strip covers no part of the plots.

Note: When the current tab holds no plot, nothing is copied (LLFR-00146, LLFR-00460), so there is no strip.

*Parent: HLFR-00039, HLFR-00113*

### LLFR-00134 HDF5 file signals
In HDF5 files, the app must read each dataset that holds a one-dimensional numeric array as one signal, in any group, named after the dataset's path in the file without the leading `/` (for example `engine/speed`).

Note: A time signal found by its name (HLFR-00006) is therefore a dataset at the top level of the file (LLFR-00330). Reading HDF5 needs a new library (COR-00011).

*Parent: HLFR-00005*

### LLFR-00455 Order of the HDF5 signals
In HDF5 files, the app must list the members of each group in the order they were created when the group tracks its creation order, as in the files of the Save signals button (LLFR-00402), and otherwise by name; the members of a group come right after the group.

*Parent: HLFR-00005*

### LLFR-00135 Other HDF5 datasets
In HDF5 files, the app must ignore datasets that do not hold a one-dimensional numeric array.

*Parent: HLFR-00005*

### LLFR-00456 Checks on the HDF5 signals read
In HDF5 files, the app must apply the checks of HLFR-00008 and HLFR-00009 only to the signals it read (LLFR-00134).

*Parent: HLFR-00005, HLFR-00008, HLFR-00009*

### LLFR-00136 Undo button
The top panel must contain a button called "Undo".

*Parent: HLFR-00040*

### LLFR-00137 Undo shortcut
The app must run the Undo button's action (LLFR-00138) when the user presses Ctrl+Z (Cmd+Z on macOS), except as in LLFR-00196.

*Parent: HLFR-00040*

### LLFR-00141 Undo unavailable
When no action is left to undo (LLFR-00139), the app must show the Undo button as disabled, in a paler color.

*Parent: HLFR-00040, HLFR-00003*

### LLFR-00457 Undo does nothing when unavailable
When no action is left to undo (LLFR-00139), neither the Undo button nor its shortcut (LLFR-00137) must do anything.

*Parent: HLFR-00040*

### LLFR-00190 Redo button
The top panel must contain a button called "Redo", placed directly to the right of the Undo button (LLFR-00136).

*Parent: HLFR-00048*

### LLFR-00191 Redo shortcut
The app must run the Redo button's action (LLFR-00192, LLFR-00444) when the user presses Ctrl+Y (Cmd+Y on macOS), except as in LLFR-00195.

*Parent: HLFR-00048*

### LLFR-00194 Redo unavailable
When no undone action is left to redo, the app must show the Redo button as disabled, in a paler color.

*Parent: HLFR-00048, HLFR-00003*

### LLFR-00458 Redo does nothing when unavailable
When no undone action is left to redo, neither the Redo button nor its shortcut (LLFR-00191) must do anything.

*Parent: HLFR-00048*

### LLFR-00145 Nothing to export
If no tab holds a plot when the user chooses "Save all tabs as PDF", the app must show an information box saying that there are no plots to export.

*Parent: HLFR-00038*

### LLFR-00459 No save dialog when nothing to export
If no tab holds a plot when the user chooses "Save all tabs as PDF", the app must not show the save file dialog (LLFR-00128).

*Parent: HLFR-00038*

### LLFR-00146 Nothing to copy
If the current tab holds no plot when the user clicks the Copy button, the app must show an information box saying that there are no plots to copy.

*Parent: HLFR-00039*

### LLFR-00460 Clipboard unchanged when nothing to copy
If the current tab holds no plot when the user clicks the Copy button, the app must not change the clipboard.

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
While the user holds down the Shift key alone, with no other keyboard key, the app must keep the Flag button (LLFR-00080) active, deactivating any other plot tool as in LLFR-00079.

*Parent: HLFR-00028, HLFR-00032*

### LLFR-00155 Release the Shift key
When the user releases the Shift key after LLFR-00154, the app must deactivate the Flag button, so that no plot tool is active, whatever plot tool was active before the Shift key was pressed.

*Parent: HLFR-00028, HLFR-00032*

### LLFR-00156 Shift key with another key
If the user presses another keyboard key while holding the Shift key (for example Shift+A), the app must end the Flag activation of LLFR-00154 as in LLFR-00155.

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
While the keyboard focus is in a text field (the search box, the search box of the second signal dialog (LLFR-00285) or of the time signal window (LLFR-00325), or a field where the user types a tab, flag, area, delta marker, arrow or synthetic signal name or a text note), the app must not apply LLFR-00148, LLFR-00154, LLFR-00197, LLFR-00200, LLFR-00207, LLFR-00454, LLFR-00287, LLFR-00321, LLFR-00367 or LLFR-00370.

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
6. Flag: a dashed vertical line with a small flag at its top;
7. Delta X: a horizontal double-headed arrow between two vertical lines;
8. Delta Y: a vertical double-headed arrow between two horizontal lines;
9. Grid: a square divided into 3 by 3 cells;
10. Export: a sheet of paper with an arrow pointing out of it;
11. Copy: two overlapping sheets of paper;
12. Redo: an arrow curving to the right;
13. Save layout: a sheet of paper with two small stacked plots and an arrow pointing down into it;
14. Load layout: a sheet of paper with two small stacked plots and an arrow pointing up out of it;
15. Area: two vertical lines with the space between them shaded;
16. Text: a capital letter T inside a small box;
17. Pan: an open hand;
18. Report a bug: a small bug;
19. Arrow: an arrow pointing up and to the right;
20. Save signals: a floppy disk with a small curve drawn on its label.

*Parent: HLFR-00042, HLFR-00048, HLFR-00049, HLFR-00050, HLFR-00066, HLFR-00073, HLFR-00036, HLFR-00078, HLFR-00081, HLFR-00090*

### LLFR-00160 Icon visibility
Each icon must be clearly visible against its button's background in the normal, active (LLFR-00001) and disabled (LLFR-00141) states.

*Parent: HLFR-00042, HLFR-00003*

### LLFR-00461 Paler icon when disabled
Each icon of a top panel button must be shown paler while its button is disabled.

*Parent: HLFR-00042, HLFR-00003*

### LLFR-00161 Delta X button
The top panel must contain a button called "Delta X".

*Parent: HLFR-00043, HLFR-00032*

### LLFR-00162 Delta Y button
The top panel must contain a button called "Delta Y".

*Parent: HLFR-00044, HLFR-00032*

### LLFR-00181 Button name on hover
When the user holds the mouse pointer over a button in the top panel, the app must show a button tip with the button's name next to the pointer.

Note: This helps a user who is starting to use the app to learn what each icon does.

*Parent: HLFR-00042*

### LLFR-00462 Button tip hidden
When the mouse pointer leaves a button in the top panel, the app must hide the button tip of LLFR-00181.

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
| Flag | Hold Shift | Hold Shift |
| Delta X | Hold X | Hold X |
| Delta Y | Hold Y | Hold Y |
| Reset zoom | Z | Z |
| Area | Hold A | Hold A |
| Text | Hold T | Hold T |
| Arrow | Hold R | Hold R |

Note: The texts of LLFR-00215, LLFR-00463, LLFR-00464 and LLFR-00465 follow LLFR-00137, LLFR-00191, LLFR-00148, LLFR-00154, LLFR-00197, LLFR-00200, LLFR-00207, LLFR-00287, LLFR-00321, LLFR-00367, LLFR-00078, LLFR-00208, LLFR-00074, LLFR-00659, LLFR-00206, LLFR-00672 and LLFR-00356.

*Parent: HLFR-00042*

### LLFR-00883 Button tip texts follow their shortcuts
When a shortcut or a mouse use that a button tip names (LLFR-00213, LLFR-00214) changes, the app must change the text of that button tip with it.

*Parent: HLFR-00042*

### LLFR-00463 Zoom button tip text
The button tip of the Zoom button (LLFR-00214) must show two lines below its name, on macOS and on Windows: "Click or drag to zoom in" and "Wheel or two-finger swipe to zoom in or out".

*Parent: HLFR-00042*

### LLFR-00464 Pan button tip text
The button tip of the Pan button (LLFR-00214) must show one line below its name, on macOS and on Windows: "Drag on a plot to pan".

*Parent: HLFR-00042*

### LLFR-00465 Button tips with only the name
The button tips of the Open file, Save layout, Load layout, Grid, Export, Copy, Save signals and Report a bug buttons must show only the button's name.

*Parent: HLFR-00042*

### LLFR-00216 Save layout button
The top panel must contain a button called "Save layout", placed directly to the right of the Open file button (LLFR-00004).

*Parent: HLFR-00049*

### LLFR-00217 Load layout button
The top panel must contain a button called "Load layout", placed directly to the right of the Save layout button (LLFR-00216).

*Parent: HLFR-00050*

### LLFR-00218 Layout buttons need a data file
While no data file is open, the app must show the Save layout and Load layout buttons as disabled, in a paler color.

*Parent: HLFR-00049, HLFR-00050, HLFR-00003*

### LLFR-00466 Layout buttons do nothing without a data file
While no data file is open, neither the Save layout button nor the Load layout button must do anything.

*Parent: HLFR-00049, HLFR-00050*

### LLFR-00219 Save layout dialog
When the user clicks the Save layout button, the app must show a save file dialog in which the user chooses the folder and types the name of the layout file.

*Parent: HLFR-00049*

### LLFR-00467 Layout file extension
If the name typed in the dialog of LLFR-00219 has no extension, the app must add `.json`.

*Parent: HLFR-00049*

### LLFR-00220 Layout dialog starting folder
The first time after the app starts that the user clicks the Save layout or Load layout button, the dialog (LLFR-00219, LLFR-00221) must show the folder that the file selection dialog of the Open file button would show at that moment (LLFR-00204, LLFR-00446, LLFR-00447).

*Parent: HLFR-00049, HLFR-00050*

### LLFR-00468 Layout dialog folder of the last layout file
After the first click on the Save layout or Load layout button since the app started (LLFR-00220), the dialog (LLFR-00219, LLFR-00221) must show the folder of the last layout file that the app saved or loaded successfully.

*Parent: HLFR-00049, HLFR-00050*

### LLFR-00221 Load layout dialog
When the user clicks the Load layout button, the app must show a file selection dialog that lists the layout files (`.json`), in which the user chooses the layout file to load.

*Parent: HLFR-00050*

### LLFR-00222 Layout dialog cancelled
If the user cancels the dialog of LLFR-00219 or LLFR-00221, the app must not save or load any file.

*Parent: HLFR-00049, HLFR-00050*

### LLFR-00469 Layout unchanged after a cancelled dialog
If the user cancels the dialog of LLFR-00219 or LLFR-00221, the app must keep the current layout unchanged.

*Parent: HLFR-00049, HLFR-00050*

### LLFR-00223 Replace an existing layout file
If the user chooses the name of a file that already exists in the dialog of LLFR-00219, after LLFR-00467 is applied, the app must ask the user whether to replace it.

*Parent: HLFR-00049*

### LLFR-00470 Layout saved only if the user agrees
When the app asks whether to replace an existing layout file (LLFR-00223), it must save the layout only if the user agrees.

*Parent: HLFR-00049*

### LLFR-00224 Layout save failure
If the layout file cannot be written, the app must show an error box saying that the layout file could not be saved.

*Parent: HLFR-00049, HLFR-00002*

### LLFR-00225 Layout file content
The layout file must hold:
1. the names of the tabs, in tab order, and which tab is shown;
2. for each tab, its time plots, from top to bottom (LLFR-00283);
3. for each time plot, its curves, in the order they were drawn, each with its signal name, color and width;
4. the x-axis range shared by the plots (LLFR-00070), in seconds;
5. whether the grid is shown (HLFR-00037);
6. under the key `flags`, for each flag, its name, its time and its color (LLFR-00392), written as `#rrggbb` in lowercase;
7. for each pinned data tip of a time plot, its plot, the signal and time of its point, and its position relative to the point;
8. for each delta marker of a time plot, its plot, its name (LLFR-00427), whether it is a Delta X or a Delta Y marker, the signal and time of each of its two points, and its color (LLFR-00409), written as `#rrggbb` in lowercase;
9. the widths of the plot panel and the signal list panel;
10. for each synthetic signal that is not an FFT signal (LLFR-00283), in the order it was created, its current name, its operation, the current names of the signals it was computed from, and its parameter: the cutoff frequency, the filter order and how the filter starts (Low-pass and High-pass filters), the window size (Moving average) or the constant (Comparison operations and Arithmetic operations with a constant); Integral, Derivative, Max, Min and Absolute value have no parameter, and the second signal of Product with signal is one of the signals it was computed from;
11. for each area, its name, start time and end time, in seconds, and its color (LLFR-00351), written as `#rrggbb` in lowercase.

*Parent: HLFR-00049, HLFR-00056, HLFR-00092, HLFR-00097*

### LLFR-00226 Not in the layout file
The layout file must not hold the names or the paths of the data files, the undo and redo history, the active plot tool, the text of the search box, the text notes or the arrows.

*Parent: HLFR-00049*

### LLFR-00943 Prefixed names in the layout file
The layout file must hold the name of each signal with its prefix of LLFR-00900, for example `file1_Speed` or `file1_int_Speed`, in its curves, pinned data tips, delta markers and synthetic signals (LLFR-00225).

*Parent: HLFR-00049, HLFR-00115*

### LLFR-00227 Layout file format
The app must write the layout file as JSON text in UTF-8, indented by 2 spaces, with each value on its own line, with keys that are English words describing their value (for example `tabs`, `plots`, `signal`, `width`), and with each time in seconds written as a decimal number with enough digits to be read back as the same value.

Note: JSON can be read and written with Python's standard library, so no new library is needed (COR-00011), and text editors such as Notepad++ highlight it.

*Parent: HLFR-00051*

### LLFR-00228 Layout file identification
The layout file must start with an entry `format` with the value `plot_tool layout` and an entry `version` with the number of the layout file format, so that the app can tell a layout file from other JSON files.

*Parent: HLFR-00051, HLFR-00050*

### LLFR-00471 Layout file format number
The number of the layout file format in the `version` entry (LLFR-00228) must be 3.

Note: Version 3 names the signals with their prefix (LLFR-00943). A file of a lower version is read as in LLFR-00958.

*Parent: HLFR-00051, HLFR-00050*

### LLFR-00472 Layout files with a lower version
A layout file with a lower `version` (LLFR-00228, LLFR-00471) must still be read, with the current rules and with no special support for the earlier format apart from the signal names of LLFR-00958, so that, for example, the flags it saved under another key are not rebuilt.

*Parent: HLFR-00051, HLFR-00050*

### LLFR-00958 Names of an older layout file
When the app loads a layout file whose `version` (LLFR-00228) is lower than 3 (LLFR-00471), it must read each signal name of the file, in its curves, pinned data tips, delta markers and synthetic signal entries (the names of the synthetic signals and of the signals they are computed from), as that name with the prefix `file1_` in front, so that `Speed` means `file1_Speed`.

Note: A synthetic signal saved as `int_Speed` is therefore created as `file1_int_Speed`, from `file1_Speed`, and its curves follow it. In a version 3 file, a name without a prefix is a missing signal (LLFR-00231).

*Parent: HLFR-00050, HLFR-00051, HLFR-00115*

### LLFR-00959 Older layout names not in the load report
The load report (LLFR-00237) must leave the names read as in LLFR-00958 out of its list, apart from the signals that are still missing after that reading, which it lists with their prefix, for example `file1_Speed`.

*Parent: HLFR-00052, HLFR-00115*

### LLFR-00229 Layout added in new tabs
When the user loads a layout file (LLFR-00221), the app must add only the tabs of the layout file that hold at least one plot once it is loaded (LLFR-00484).

Note: Loading a layout never asks for confirmation, because it removes no plot. It also keeps the current synthetic signals (LLFR-00495).

*Parent: HLFR-00050*

### LLFR-00473 Current tabs kept on layout load
When the user loads a layout file (LLFR-00221) and the current tabs hold at least one plot, the app must keep the current tabs, with their plots, curves, pinned data tips, delta markers, text notes and arrows, unchanged.

*Parent: HLFR-00050*

### LLFR-00474 Layout tabs after the current tabs
When the user loads a layout file (LLFR-00221) and the current tabs hold at least one plot, the app must add the tabs of the layout file of LLFR-00229 after the last current tab.

*Parent: HLFR-00050*

### LLFR-00475 Layout tabs replace tabs with no plot
When the user loads a layout file (LLFR-00221) and no current tab holds a plot, the app must replace the current tabs with the tabs of the layout file of LLFR-00229, except as in LLFR-00476.

*Parent: HLFR-00050*

### LLFR-00476 Current tabs kept when the layout adds no tab
When the user loads a layout file (LLFR-00221) and no tab of the layout file holds a plot, the app must keep the current tabs, so that at least one tab always exists (LLFR-00066).

*Parent: HLFR-00050*

### LLFR-00477 First added tab shown
When the user loads a layout file (LLFR-00221), the app must show the first tab it added from the layout file.

*Parent: HLFR-00050*

### LLFR-00230 Rebuild the layout
When the app loads a layout file, it must build the tabs that hold at least one plot (LLFR-00484), and the plots, curves, delta markers and pinned data tips of the file, in the file's order, in the tabs of LLFR-00229, LLFR-00474 and LLFR-00475, using the signals of the open data files (LLFR-00944) and the synthetic signals of LLFR-00262, except as in LLFR-00231 to LLFR-00235, LLFR-00483, LLFR-00484, LLFR-00485, LLFR-00486, LLFR-00487, LLFR-00488, LLFR-00489, LLFR-00319, LLFR-00726, LLFR-00728, LLFR-00393, LLFR-00815, LLFR-00816, LLFR-00410, LLFR-00822 and LLFR-00823.

*Parent: HLFR-00050*

### LLFR-00944 Curves matched by file number
When loading a layout, the app must draw each curve with the signal of the signal list whose name is the saved name, so that a saved name that starts with `file<N>_` is drawn with a signal of the data file that has the number N at that moment.

Note: A curve whose file number is not open, or whose file has no signal of that name, is a missing signal (LLFR-00231) and is named in the load report (LLFR-00237). The layout file still holds no file name or path (LLFR-00226).

*Parent: HLFR-00050, HLFR-00052, HLFR-00115*

### LLFR-00965 Synthetic signal of a layout with a wrong prefix
When a synthetic signal of a layout file (LLFR-00262) has a saved name that does not start with the prefix of its own data file (LLFR-00900, LLFR-00935), the app must create it with that prefix in place of the prefix of another file, or in front of the name when it has no prefix.

Note: For example, `my_int` computed from `file2_Speed` becomes `file2_my_int`, and `file1_x` computed from `file2_Speed` becomes `file2_x`. LLFR-00499 then applies to the new name. The rename is listed under "Renamed:" (LLFR-00237, LLFR-00501), and the curves follow the new name (LLFR-00500). In a file of an older version, LLFR-00958 gives every name the prefix `file1_` first.

*Parent: HLFR-00050, HLFR-00052, HLFR-00115*

### LLFR-00478 Flags added from a layout
When the app loads a layout file (LLFR-00230), it must add the flags of the file to the current ones (LLFR-00205), except as in the requirements that LLFR-00230 names as exceptions.

*Parent: HLFR-00050*

### LLFR-00479 Areas added from a layout
When the app loads a layout file (LLFR-00230), it must add the areas of the file to the current ones (LLFR-00310), except as in the requirements that LLFR-00230 names as exceptions.

*Parent: HLFR-00050*

### LLFR-00480 Time range applied from a layout
When the app loads a layout file (LLFR-00230), it must apply the file's time range to every plot (LLFR-00070), except as in the requirements that LLFR-00230 names as exceptions.

*Parent: HLFR-00050*

### LLFR-00481 Grid setting applied from a layout
When the app loads a layout file (LLFR-00230), it must apply the file's grid setting to every plot (LLFR-00122, LLFR-00123), except as in the requirements that LLFR-00230 names as exceptions.

*Parent: HLFR-00050*

### LLFR-00482 Panel widths applied from a layout
When the app loads a layout file (LLFR-00230), it must apply the file's panel widths, except as in the requirements that LLFR-00230 names as exceptions.

*Parent: HLFR-00050*

### LLFR-00231 Missing signals in a layout
When loading a layout, the app must not draw a curve whose signal is not in the open data files (LLFR-00944).

*Parent: HLFR-00050, HLFR-00052*

### LLFR-00483 No plot with no curve from a layout
When loading a layout, the app must not create a plot that is left with no curve.

*Parent: HLFR-00050, HLFR-00052*

### LLFR-00484 No tab with no plot from a layout
When loading a layout, the app must not create a tab of the file that is left with no plot, whether the tab was saved with no plot or all its plots were left out (for example because their signals are missing, or because they were frequency plots, LLFR-00283).

Note: A tab that is not created is not listed on its own in the load report (LLFR-00492): the missing signals of its plots already explain it.

*Parent: HLFR-00050, HLFR-00052*

### LLFR-00232 Data tips and delta markers in a layout
When loading a layout, the app must rebuild a pinned data tip or a delta marker only if the signal of each of its points is drawn in its plot and has a sample whose time differs from the saved time by at most 1 microsecond.

*Parent: HLFR-00050, HLFR-00052*

### LLFR-00485 Points placed on the saved sample
When the app rebuilds a pinned data tip or a delta marker from a layout (LLFR-00232), it must place each of its points on the sample whose time differs from the saved time by at most 1 microsecond.

*Parent: HLFR-00050, HLFR-00052*

### LLFR-00486 No delta marker of value zero from a layout
When loading a layout, the app must not rebuild a delta marker whose value on the samples of LLFR-00485 would be zero (LLFR-00431).

*Parent: HLFR-00050, HLFR-00052, HLFR-00098*

### LLFR-00233 Flags in a layout
When loading a layout, the app must rebuild a flag only if its time is within the time range of the open data files (LLFR-00911).

*Parent: HLFR-00050, HLFR-00052*

### LLFR-00234 Time range in a layout
When loading a layout, the app must limit the saved x-axis range to the time range of the open data files (LLFR-00911, LLFR-00119), except as in LLFR-00487.

*Parent: HLFR-00050, HLFR-00052*

### LLFR-00487 Saved time range outside the files
When loading a layout, if the saved x-axis range does not overlap the time range of the open data files (LLFR-00911), the app must show that whole time range.

*Parent: HLFR-00050, HLFR-00052*

### LLFR-00235 Unusable values in a layout
When loading a layout, the app must replace a value it cannot use with the value it would use for a new item: a curve width that is not one of the preset widths 1 to 5 with width 1 (LLFR-00052), a curve color that is not valid, is already used in the plot or is closer than 70 to the reserved marker color (LLFR-00365) with the next color of LLFR-00033 and LLFR-00034, and the name of a tab it creates (LLFR-00484) that is empty, is not a text or is the name of an earlier tab it created from the same layout file with a name as in LLFR-00210 and LLFR-00653.

Note: Such values appear only when the file was edited by hand, unlike the tab names already in use of LLFR-00489.

*Parent: HLFR-00050, HLFR-00052*

### LLFR-00488 Plots beyond the maximum in a layout
When loading a layout, the app must not create the plots of a tab beyond the maximum of HLFR-00018.

*Parent: HLFR-00050, HLFR-00052*

### LLFR-00489 Tab name already in use in a layout
When loading a layout, the app must replace a tab name of the file that is valid but is already the name of another tab, for example a kept tab (LLFR-00473) or a tab created earlier in the same load, with a name as in LLFR-00210 and LLFR-00653.

*Parent: HLFR-00050, HLFR-00052*

### LLFR-00490 Tab rename in the load report
Each tab rename of LLFR-00489 must be listed in the load report (LLFR-00237).

*Parent: HLFR-00050, HLFR-00052*

### LLFR-00236 Unreadable layout file
If the chosen file cannot be read, is not valid JSON or does not identify itself as a layout file (LLFR-00228), the app must show an error box saying that the file could not be read as a layout file.

*Parent: HLFR-00050, HLFR-00002*

### LLFR-00491 Layout unchanged after an unreadable file
If the chosen file cannot be read, is not valid JSON or does not identify itself as a layout file (LLFR-00228), the app must keep the current layout unchanged.

*Parent: HLFR-00050*

### LLFR-00237 Layout load report
After loading a layout, if any part of it was not rebuilt or was changed (LLFR-00231 to LLFR-00235, LLFR-00483, LLFR-00484, LLFR-00485, LLFR-00486, LLFR-00487, LLFR-00488, LLFR-00489, LLFR-00262, LLFR-00496, LLFR-00282, LLFR-00499, LLFR-00283, LLFR-00502, LLFR-00319, LLFR-00726, LLFR-00728, LLFR-00393, LLFR-00817, LLFR-00410, LLFR-00824), the app must show one information box that lists, except as in LLFR-00492: the signals that are not in the open data files, each named once; each synthetic signal that was not created, with the reason; each tab and each synthetic signal of the file that was renamed because its name was in use or did not start with the prefix of its data file (LLFR-00489, LLFR-00499, LLFR-00965), under the heading "Renamed:", as `<saved name> → <new name>`; each pinned data tip, flag, area and delta marker that was not rebuilt, with its time and the reason; the time range when it was changed; and each value that was replaced.

Note: The box is an information box, not an error box (HLFR-00002), like the Full Tab Notification box (LLFR-00032).

*Parent: HLFR-00052*

### LLFR-00884 Scrollable load report
The information box of LLFR-00237 must be scrollable when its list is longer than the box can show.

*Parent: HLFR-00052*

### LLFR-00492 Parts not listed on their own in the load report
The load report of LLFR-00237 must not list on their own a tab of the file that is not created (LLFR-00484) and a synthetic signal reused as in LLFR-00282.

*Parent: HLFR-00052*

### LLFR-00493 No load report when all is rebuilt
After loading a layout, if everything was rebuilt as saved, the app must not show any message.

*Parent: HLFR-00052*

### LLFR-00238 Undo history on layout load
When the app loads a layout, it must clear the undo and redo history, as when a data file is closed (LLFR-00925).

*Parent: HLFR-00050, HLFR-00040, HLFR-00048*

### LLFR-00494 Saving and loading a layout not undoable
Saving and loading a layout must not be undoable actions (LLFR-00140).

*Parent: HLFR-00050, HLFR-00040, HLFR-00048*

### LLFR-00262 Synthetic signals on layout load
When the app loads a layout file (LLFR-00230), before it rebuilds the plots, it must create the synthetic signals of the file, in the file's order, with their saved names except as in LLFR-00965, LLFR-00282 and LLFR-00499 (each rename is listed in the load report, LLFR-00237), using the saved operation, signals and parameter (LLFR-00225), except as in LLFR-00496.

*Parent: HLFR-00056, HLFR-00050, HLFR-00052*

### LLFR-00495 Current synthetic signals kept on layout load
When the app loads a layout file (LLFR-00230), before it rebuilds the plots, it must keep the current synthetic signals and their curves.

*Parent: HLFR-00056, HLFR-00050, HLFR-00052*

### LLFR-00496 Synthetic signals not created from a layout
When the app loads a layout file (LLFR-00262), a synthetic signal of the file must not be created when it is an FFT signal (LLFR-00502), when its entry cannot be read, when a signal it is computed from is missing, was not created or comes later in the list, when the signals it is computed from belong to different data files whose time signals are not the same (LLFR-00275, LLFR-00935), when its parameter is not allowed (LLFR-00245, LLFR-00269, LLFR-00272, LLFR-00613), or when the operation cannot be done (LLFR-00590).

*Parent: HLFR-00056, HLFR-00050, HLFR-00052*

### LLFR-00497 Curves of a synthetic signal not created
When a synthetic signal of the layout file is not created (LLFR-00496), its curves must be treated as curves of a missing signal (LLFR-00231), even when another signal of the signal list has its name.

*Parent: HLFR-00056, HLFR-00050, HLFR-00052*

### LLFR-00498 Synthetic signal not created in the load report
When a synthetic signal of the layout file is not created (LLFR-00496), the load report (LLFR-00237) must name it with the reason.

*Parent: HLFR-00056, HLFR-00050, HLFR-00052*

### LLFR-00282 Synthetic signal names on layout load
When a synthetic signal of the layout file (LLFR-00262) has the name of a signal of the signal list, which is a current synthetic signal, one created earlier in the same load or a signal of an open data file, and that signal, or a synthetic signal whose name is made from that name as in LLFR-00241 (for example by an earlier load), has the same operation, the same signals it is computed from (after the renames of LLFR-00499) and the same parameter, the app must create nothing and use that signal.

Note: Loading the same layout twice therefore adds nothing to the signal list the second time.

*Parent: HLFR-00050, HLFR-00056*

### LLFR-00499 Renamed synthetic signal on layout load
When a synthetic signal of the layout file (LLFR-00262) has the name of a signal of the signal list, which is a current synthetic signal, one created earlier in the same load or a signal of an open data file, and no signal is used in its place as in LLFR-00282, the app must create the signal of the file with its name made unique as in LLFR-00241.

*Parent: HLFR-00050, HLFR-00056*

### LLFR-00500 New name used in the layout
When the app creates a synthetic signal of the layout file with a new name (LLFR-00499, LLFR-00965), it must use the new name for every curve, pinned data tip and delta marker of the file that names it, and for every later synthetic signal of the file that is computed from it.

*Parent: HLFR-00050, HLFR-00056, HLFR-00115*

### LLFR-00501 Synthetic signal rename in the load report
Each rename of LLFR-00499 or LLFR-00965 must be listed in the load report (LLFR-00237), with the saved and the new name.

*Parent: HLFR-00050, HLFR-00056, HLFR-00115*

### LLFR-00283 FFT signals not in the layout file
The layout file must not hold the FFT signals, the frequency plots (HLFR-00058), or the curves, pinned data tips and delta markers of frequency plots. A tab is still saved when all its plots are frequency plots; such a tab is not created when the layout is loaded (LLFR-00484).

*Parent: HLFR-00049, HLFR-00056*

### LLFR-00502 FFT signal entry not created from a layout
When a layout file being loaded holds the entry of an FFT signal in its list of synthetic signals (for example after a hand edit, or in an older file), the app must not create that FFT signal.

*Parent: HLFR-00049, HLFR-00056*

### LLFR-00503 FFT signal entry in the load report
When a layout file being loaded holds the entry of an FFT signal in its list of synthetic signals (LLFR-00502), the app must list it in the load report (LLFR-00237) with the reason that FFT signals are not loaded from layout files.

*Parent: HLFR-00049, HLFR-00056*

### LLFR-00504 Curves of an FFT signal entry
When a layout file being loaded holds the entry of an FFT signal in its list of synthetic signals (LLFR-00502), the curves of that FFT signal must be treated as curves of a missing signal (LLFR-00231).

*Parent: HLFR-00049, HLFR-00056*

### LLFR-00286 Area button
The top panel must contain a button called "Area".

*Parent: HLFR-00066, HLFR-00032*

### LLFR-00287 Hold the A key
While the user holds down the A key alone, with no other keyboard key, the app must keep the Area button (LLFR-00286) active, deactivating any other plot tool as in LLFR-00079.

*Parent: HLFR-00066, HLFR-00032*

### LLFR-00288 Release the A key
When the user releases the A key after LLFR-00287, the app must deactivate the Area button, so that no plot tool is active, whatever plot tool was active before the A key was pressed.

*Parent: HLFR-00066, HLFR-00032*

### LLFR-00289 A key with another key
If the user presses another keyboard key while holding the A key, the app must end the Area activation of LLFR-00287 as in LLFR-00288.

*Parent: HLFR-00066, HLFR-00032*

### LLFR-00320 Text button
The top panel must contain a button called "Text".

*Parent: HLFR-00073, HLFR-00032*

### LLFR-00321 Hold the T key
While the user holds down the T key alone, with no other keyboard key, the app must keep the Text button (LLFR-00320) active, deactivating any other plot tool as in LLFR-00079.

*Parent: HLFR-00073, HLFR-00032*

### LLFR-00322 Release the T key
When the user releases the T key after LLFR-00321, the app must deactivate the Text button, so that no plot tool is active, whatever plot tool was active before the T key was pressed.

*Parent: HLFR-00073, HLFR-00032*

### LLFR-00323 T key with another key
If the user presses another keyboard key while holding the T key, the app must end the Text activation of LLFR-00321 as in LLFR-00322.

*Parent: HLFR-00073, HLFR-00032*

### LLFR-00324 Several signals named Time
When more than one signal of a file matches the time signal name (LLFR-00053), the app must use the signal named exactly `Time` or, if there is none, the first matching signal in the file's order.

*Parent: HLFR-00006*

### LLFR-00505 No choice with several signals named Time
When more than one signal of a file matches the time signal name (LLFR-00053), the app must not ask the user to choose.

*Parent: HLFR-00006*

### LLFR-00325 Time signal window
When no signal of a file matches the time signal name (LLFR-00053), the app must show a window with the text "Choose the signal that goes on the x-axis", a list of all the signals of the file in the file's order, and a search box above the list that works as in LLFR-00285, LLFR-00618, LLFR-00619, LLFR-00620 and LLFR-00621.

*Parent: HLFR-00070, HLFR-00033*

### LLFR-00506 Focus in the time signal window
When the window of LLFR-00325 opens, the keyboard focus must be in its search box.

*Parent: HLFR-00070, HLFR-00033*

### LLFR-00326 Time signal chosen
When the user confirms a signal in the window of LLFR-00325, the app must use that signal as the time signal of that data file in every requirement that applies to the time signal, including HLFR-00007.

Note: The chosen signal is therefore treated as seconds, and it stays in the signal list (LLFR-00054).

*Parent: HLFR-00070, HLFR-00006, HLFR-00007*

### LLFR-00507 Opening continues after the choice
When the user confirms a signal in the window of LLFR-00325, the app must continue opening the file.

*Parent: HLFR-00070, HLFR-00006*

### LLFR-00327 Time signal window cancelled
If the user cancels the window of LLFR-00325, the app must not open the file.

*Parent: HLFR-00070, HLFR-00004*

### LLFR-00508 Files kept after a cancelled time signal window
If the user cancels the window of LLFR-00325, the app must keep the open data files unchanged as in LLFR-00010.

*Parent: HLFR-00070, HLFR-00004*

### LLFR-00509 No message after a cancelled time signal window
If the user cancels the window of LLFR-00325, the app must not show any message.

*Parent: HLFR-00070, HLFR-00004*

### LLFR-00328 Order of the opening steps
For each selected file (LLFR-00006, LLFR-00947), the app must take these steps in this order:
1. if 10 data files are open, refuse the file (LLFR-00949) and go on with the next one;
2. if the file is already open as a data file, refuse it (LLFR-00893) and go on with the next one;
3. read the file and apply the checks of HLFR-00008 and HLFR-00009 to it, showing the indication of LLFR-00418 and LLFR-00560, and, if it cannot be opened, keep it for the box of LLFR-00950 and go on with the next one;
4. show the window of LLFR-00325 for this file if it is needed, and go on with the next file if the window is cancelled;
5. only then add the file as the next data file (LLFR-00895, LLFR-00915) and show its file name row and its signals (LLFR-00933, LLFR-00934).

Note: A file with fewer than two signals therefore fails with LLFR-00012 and never shows the window. The boxes of LLFR-00950 and LLFR-00951 come after the last selected file. The limit of 10 files is also checked before the file selection dialog opens (LLFR-00891).

*Parent: HLFR-00070, HLFR-00008, HLFR-00009, HLFR-00004, HLFR-00101, HLFR-00113, HLFR-00117, HLFR-00122*

### LLFR-00510 Error box at the reading step
If a selected file cannot be opened at step 3 of LLFR-00328 (any File Open Error box, for example LLFR-00008, LLFR-00009, LLFR-00011, LLFR-00012, LLFR-00064 or LLFR-00065), the app must list that file with the reason of that error in the one File Open Error box of LLFR-00950.

*Parent: HLFR-00008, HLFR-00009, HLFR-00004, HLFR-00122*

### LLFR-00511 Files kept after an error at the reading step
If the file cannot be opened at step 3 of LLFR-00328, the app must keep the open data files as in LLFR-00010.

*Parent: HLFR-00008, HLFR-00009, HLFR-00004, HLFR-00101*

### LLFR-00512 Files kept after a cancel at the window step
If the window of step 4 of LLFR-00328 is cancelled, the app must keep the open data files as in LLFR-00010.

*Parent: HLFR-00070, HLFR-00004*

### LLFR-00513 No message after a cancel at the window step
If the window of step 4 of LLFR-00328 is cancelled, the app must show no message (LLFR-00509).

*Parent: HLFR-00070, HLFR-00004*

### LLFR-00329 Chosen signal must increase
If the user confirms a signal in the window of LLFR-00325 in which any sample is not greater than the sample before it, the window must stay open.

Note: Zoom and pan use the first and last samples as the limits of the time range (LLFR-00119).

*Parent: HLFR-00070*

### LLFR-00514 Message for a signal that does not increase
If the user confirms a signal in the window of LLFR-00325 in which any sample is not greater than the sample before it, the window must say that the signal on the x-axis has to always increase.

*Parent: HLFR-00070*

### LLFR-00330 Time signal in an HDF5 group
In HDF5 files, only a dataset at the top level of the file must match the time signal name (LLFR-00053), so that a dataset such as `engine/time` is not found automatically. The user can still choose it in the window of LLFR-00325.

*Parent: HLFR-00006, HLFR-00005*

### LLFR-00331 No later change of the time signal
The app must not offer any button, menu option or other control that changes the time signal of an opened file.

*Parent: HLFR-00072*

### LLFR-00515 Time signal changed only by reopening the file
The app must not change the time signal of an open data file except when the file is closed (LLFR-00919, LLFR-00929) and opened again.

Note: Reopening a file that has a signal matching the time signal name does not show the window of LLFR-00325 (HLFR-00070).

*Parent: HLFR-00072*

### LLFR-00347 Order of the button groups
The top panel must show its buttons in this order, from left to right, in these groups:
1. Open file, Save layout, Load layout;
2. Data tip, Zoom, Pan, Flag, Delta X, Delta Y, Area, Text, Arrow;
3. Reset zoom, Grid;
4. Export, Copy, Save signals;
5. Undo, Redo;
6. Report a bug.

*Parent: HLFR-00077*

### LLFR-00348 Joined buttons
The buttons of a group (LLFR-00347) must have no space between them.

*Parent: HLFR-00102*

### LLFR-00516 Shared border of a group
The buttons of a group (LLFR-00347) must share one border line, with rounded corners only on the outer side of the group's first and last buttons.

*Parent: HLFR-00102*

### LLFR-00349 Space between groups
The top panel must leave a space of 16 pixels between one button group (LLFR-00347) and the next.

*Parent: HLFR-00103*

### LLFR-00350 Button states inside a group
Each button of a group (LLFR-00347) must keep showing its own state, normal, active (LLFR-00001) or disabled (LLFR-00141, LLFR-00194, LLFR-00218, LLFR-00395), whatever the state of the other buttons of the group.

*Parent: HLFR-00077, HLFR-00003*

### LLFR-00355 Pan button
The top panel must contain a button called "Pan".

*Parent: HLFR-00036, HLFR-00032*

### LLFR-00358 Report a bug button
The top panel must contain a button called "Report a bug".

*Parent: HLFR-00078*

### LLFR-00517 Report a bug button always enabled
The Report a bug button (LLFR-00358) must be enabled whether or not a data file is open.

*Parent: HLFR-00078*

### LLFR-00359 Report a bug action
When the user clicks the Report a bug button, the app must open the page `https://github.com/materodr/plot_tool/issues/new/choose` in the system's default web browser, the same page as the "New issue" button of the repository on GitHub.

*Parent: HLFR-00078*

### LLFR-00518 Report a bug changes nothing
When the user clicks the Report a bug button, the app must leave the open data files, the plots and the undo and redo history unchanged.

*Parent: HLFR-00078*

### LLFR-00360 Report a bug button feedback
When the user clicks the Report a bug button, the button must show its active color (LLFR-00001) until the app has asked the browser to open the page, and for at least 0.3 seconds.

*Parent: HLFR-00078, HLFR-00003*

### LLFR-00519 Report a bug button back to normal
After the Report a bug button has shown its active color as in LLFR-00360, the button must return to its normal color (LLFR-00003).

*Parent: HLFR-00078, HLFR-00003*

### LLFR-00361 Browser cannot be opened
If the app cannot open the web browser, it must show an error box saying that the page could not be opened, with the page's address.

*Parent: HLFR-00078, HLFR-00002*

### LLFR-00364 Credit text
The top panel must show the text "Designed by materodr", with a capital D, at its right end, in a paler color than the panel's normal text.

*Parent: HLFR-00080*

### LLFR-00520 Credit text is not a button
The credit text of LLFR-00364 must not be a button.

*Parent: HLFR-00080*

### LLFR-00521 Credit text ignores the mouse
The credit text of LLFR-00364 must not react to the mouse.

*Parent: HLFR-00080*

### LLFR-00522 Credit text hidden in a narrow window
When the window is too narrow for the buttons and the credit text of LLFR-00364, the app must hide the text.

*Parent: HLFR-00080*

### LLFR-00523 Buttons kept in a narrow window
When the window is too narrow for the buttons and the credit text of LLFR-00364, the app must not cover or move any button.

*Parent: HLFR-00080*

### LLFR-00889 Author name underlined in the credit text
In the credit text of LLFR-00364, only the word "materodr" must be underlined.

*Parent: HLFR-00080*

### LLFR-00365 Curve palette against the marker color
Every color of the palette of LLFR-00033 must be at a distance of at least 70 from the reserved marker color (LLFR-00083), measured as the Euclidean distance between their red, green and blue values from 0 to 255.

*Parent: HLFR-00020, HLFR-00028*

### LLFR-00524 No orange in the curve palette
As a result of LLFR-00365, the palette of LLFR-00033 must not contain an orange.

*Parent: HLFR-00020, HLFR-00028*

### LLFR-00525 Palette red darker than the marker color
As a result of LLFR-00365, the red of the palette of LLFR-00033 must be darker than the reserved marker color (LLFR-00083).

*Parent: HLFR-00020, HLFR-00028*

### LLFR-00366 Arrow button
The top panel must contain a button called "Arrow".

*Parent: HLFR-00081, HLFR-00032*

### LLFR-00367 Hold the R key
While the user holds down the R key alone, with no other keyboard key, the app must keep the Arrow button (LLFR-00366) active, deactivating any other plot tool as in LLFR-00079.

*Parent: HLFR-00081, HLFR-00032*

### LLFR-00368 Release the R key
When the user releases the R key after LLFR-00367, the app must deactivate the Arrow button, so that no plot tool is active, whatever plot tool was active before the R key was pressed.

*Parent: HLFR-00081, HLFR-00032*

### LLFR-00369 R key with another key
If the user presses another keyboard key while holding the R key, the app must end the Arrow activation of LLFR-00367 as in LLFR-00368.

*Parent: HLFR-00081, HLFR-00032*

### LLFR-00370 Esc key switches off the plot tool
When the user presses the Esc key alone, with no other keyboard key, while a plot tool is active, the app must deactivate the active plot tool button, so that no plot tool is active (LLFR-00382, LLFR-00790, LLFR-00791, LLFR-00792, LLFR-00793, LLFR-00794, LLFR-00795 and LLFR-00796), except as in LLFR-00528, LLFR-00529 and LLFR-00530.

Note: The Esc key has no button, so it is not shown in any button tip (LLFR-00215, LLFR-00463, LLFR-00464, LLFR-00465).

*Parent: HLFR-00032, HLFR-00085*

### LLFR-00526 Esc key with no plot tool
While no plot tool is active, the Esc key must do nothing.

*Parent: HLFR-00032, HLFR-00085*

### LLFR-00527 No message for the Esc key with no plot tool
While no plot tool is active, the Esc key must not show any message.

*Parent: HLFR-00032, HLFR-00085*

### LLFR-00528 Esc key in text fields, menus and dialogs
While the keyboard focus is in a text field (LLFR-00157), or while a menu or a dialog is open, the Esc key must keep its own meaning there (for example, it cancels a text note, LLFR-00335, LLFR-00737 and LLFR-00738, or closes the menu).

*Parent: HLFR-00032, HLFR-00085*

### LLFR-00529 Plot tool kept by the Esc key in text fields, menus and dialogs
While the keyboard focus is in a text field (LLFR-00157), or while a menu or a dialog is open, the Esc key must not change the plot tool.

*Parent: HLFR-00032, HLFR-00085*

### LLFR-00530 Esc key while dragging
While the user is dragging the mouse (LLFR-00454), the Esc key must do nothing.

*Parent: HLFR-00032, HLFR-00085*

### LLFR-00394 Save signals button
The top panel must contain a button called "Save signals", placed directly to the right of the Copy button (LLFR-00132).

*Parent: HLFR-00090*

### LLFR-00395 Save signals button needs a data file
While no data file is open, the app must show the Save signals button as disabled, in a paler color.

*Parent: HLFR-00090, HLFR-00003*

### LLFR-00531 Save signals button does nothing without a data file
While no data file is open, the Save signals button must do nothing.

*Parent: HLFR-00090*

### LLFR-00396 Save signals dialog
When the user clicks the Save signals button, the app must show a save file dialog in which the user chooses the folder, types the name of the file and chooses its format among CSV (`.csv`), Excel (`.xlsx`), MAT (`.mat`) and HDF5 (`.h5`, `.hdf5`) (HLFR-00005), except as in LLFR-00937.

*Parent: HLFR-00090*

### LLFR-00937 Different time signals
When the user clicks the Save signals button (LLFR-00394) and the time signals of the open data files do not all have the same number of samples and exactly the same value at every sample, the app must show, in place of the save file dialog (LLFR-00396), an error box saying that the files need the same time signals to be saved together.

Note: With one data file open, the check always passes.

*Parent: HLFR-00120, HLFR-00090, HLFR-00002*

### LLFR-00938 No file written with different time signals
In the case of LLFR-00937, the app must leave every file on disk as it was.

*Parent: HLFR-00120, HLFR-00090*

### LLFR-00939 One time signal in the saved file
When the time signals of the open data files are the same (LLFR-00937), the saved file must hold, once and in place of the time signals of all the open data files, the time signal of the open data file with the lowest number, at its place in the signal list, under the name of LLFR-00407.

*Parent: HLFR-00120, HLFR-00090*

### LLFR-00940 Plain names in the saved file
The app must save each signal under its plain name, which is its name with every prefix of LLFR-00900 removed that the app put into it (LLFR-00900, LLFR-00903, LLFR-00953, LLFR-00954), keeping the text that the user typed when renaming a synthetic signal (LLFR-00266) as it was typed.

Note: For example, `file1_Speed` is saved as `Speed`, `file1_int_Speed` as `int_Speed`, `file1_lpf_2Hz_order2_Speed` as `lpf_2Hz_order2_Speed`, `file1_Speed_prod_Torque` and `file1_Speed_prod_file2_Torque` as `Speed_prod_Torque`, and a synthetic signal renamed `file1_my` (LLFR-00954) as `my`.

*Parent: HLFR-00121, HLFR-00090*

### LLFR-00941 Plain name shared by several signals
When two or more saved signals other than the time signal (LLFR-00939) have the same plain name (LLFR-00940), the app must add to the plain name of each of them an underscore and the number of its own data file (LLFR-00895, LLFR-00935), except as in LLFR-00960.

Note: For example, `file1_Speed` and `file2_Speed` are saved as `Speed_1` and `Speed_2`, `file3_Speed` and `file5_Speed` as `Speed_3` and `Speed_5`, and `file1_int_Speed` and `file2_int_Speed` as `int_Speed_1` and `int_Speed_2`. A signal whose plain name no other saved signal has keeps it with no number.

*Parent: HLFR-00121, HLFR-00090*

### LLFR-00960 Name still shared after the file number
When a name made by LLFR-00941 is still the name of another saved signal, the app must add to the name of the later of the two signals in the order of LLFR-00401 an underscore and the smallest number from 2 up that makes it unique, as in LLFR-00241.

Note: For example, with `file1_Speed`, `file2_Speed` and `file1_Speed_2`, the plain name `Speed` is shared, so `file1_Speed` and `file2_Speed` become `Speed_1` and `Speed_2`. `file1_Speed_2` keeps its plain name `Speed_2`, because no other signal has that plain name. `Speed_2` from `file2_Speed` comes later in the list (LLFR-00934), so it becomes `Speed_2_2`.

*Parent: HLFR-00121, HLFR-00090*

### LLFR-00942 Order of the name changes
When the app saves the signals, it must apply LLFR-00940, LLFR-00941 and LLFR-00960, in this order, before the rules of LLFR-00403, LLFR-00407 and LLFR-00557.

*Parent: HLFR-00121, HLFR-00090*

### LLFR-00532 Save signals dialog first values
The dialog of LLFR-00396 must open in the folder of the open data file with the lowest number (LLFR-00895), with that file's name without its extension, followed by `_signals` and that file's extension, and with that file's format chosen; for example `run1_signals.csv` for `run1.csv`.

*Parent: HLFR-00090*

### LLFR-00533 Save signals file extension
If the name typed in the dialog of LLFR-00396 does not end with an extension of the chosen format, the app must add `.csv`, `.xlsx`, `.mat` or `.h5`.

*Parent: HLFR-00090*

### LLFR-00397 Open data files not replaced
If the file chosen in the dialog of LLFR-00396 is one of the open data files, the app must not save any file.

*Parent: HLFR-00090, HLFR-00105*

### LLFR-00534 Error box for an open data file
If the file chosen in the dialog of LLFR-00396 is one of the open data files, the app must show an error box saying that an open data file cannot be replaced (LLFR-00253).

*Parent: HLFR-00090, HLFR-00002, HLFR-00105*

### LLFR-00535 No question to replace an open data file
When the user saves the signals (LLFR-00396), the app itself must never ask whether to replace an open data file.

Note: On a system whose own save file dialog always asks before replacing an existing file, such as macOS, that system question may appear before the error box (LLFR-00534) when the user chooses an open data file; the app keeps the system's native dialog and does not ask again.

*Parent: HLFR-00090, HLFR-00105*

### LLFR-00536 Replace an existing signals file
If the file chosen in the dialog of LLFR-00396, after LLFR-00533 is applied, is not one of the open data files and is the name of a file that already exists, the app must ask the user whether to replace it.

*Parent: HLFR-00090*

### LLFR-00537 Signals saved only if the user agrees
When the app asks whether to replace an existing file (LLFR-00536), it must save the file only if the user agrees.

*Parent: HLFR-00090*

### LLFR-00538 No second replace question
When the system's save file dialog has already asked the user whether to replace the file (LLFR-00536), the app must not ask a second time.

*Parent: HLFR-00090*

### LLFR-00398 Save signals cancelled
If the user cancels the dialog of LLFR-00396 or the question of LLFR-00536, the app must not save any file.

*Parent: HLFR-00090*

### LLFR-00539 No message after a cancelled save of the signals
If the user cancels the dialog of LLFR-00396 or the question of LLFR-00536, the app must not show any message.

*Parent: HLFR-00090*

### LLFR-00399 Save signals failure
If the file cannot be written, the app must show an error box saying that the file could not be saved.

*Parent: HLFR-00090, HLFR-00002*

### LLFR-00400 Too many signals or samples for Excel
If the signals to save (LLFR-00401) do not fit in one Excel sheet, which holds at most 16384 columns and 1048576 rows, so at most 16384 signals of at most 1048575 samples below the row of names, the app must not write the file.

*Parent: HLFR-00090*

### LLFR-00540 Error box for too many signals or samples for Excel
If the signals to save (LLFR-00401) do not fit in one Excel sheet (LLFR-00400), the app must show an error box saying that the signals have too many samples or are too many for an Excel file.

*Parent: HLFR-00090, HLFR-00002*

### LLFR-00401 Saved signals
The saved file must hold every signal of the signal list, in the order of the list, with all its samples, including the synthetic signals and the one time signal of LLFR-00939, except the FFT signals and the other time signals, which the app leaves out.

*Parent: HLFR-00090*

### LLFR-00541 FFT signals left out without a message
The app must leave the FFT signals out of the saved file (LLFR-00401) without any message.

*Parent: HLFR-00090*

### LLFR-00402 Saved file opens as a data file
The app must write the saved file following the reading rules of its format, so that opening it (LLFR-00006) shows the same signals, with the names of LLFR-00940, LLFR-00941, LLFR-00960, LLFR-00403, LLFR-00407 and LLFR-00557 behind the prefix of its new file number (LLFR-00900), and the same values:
1. CSV: one column per signal with the signal names in the first row (LLFR-00059, LLFR-00451), with `,` as the separator and `.` as the decimal mark (LLFR-00061);
2. Excel: the same columns in the first and only sheet (LLFR-00059, LLFR-00060);
3. MAT: one top-level variable holding a one-dimensional numeric array per signal (LLFR-00062), in a MAT format that is not v7.3 (LLFR-00064);
4. HDF5: one dataset holding a one-dimensional numeric array per signal, at the path given by the signal's name, so that a `/` in the name puts the dataset in groups (LLFR-00134).

*Parent: HLFR-00090, HLFR-00005*

### LLFR-00542 Precision of the saved values
Each value of the saved file (LLFR-00402) must be written with enough digits, or as a 64-bit floating-point number, to be read back as the same value.

Note: A value of `-0.0` may be read back from an Excel file as `0`, which is the same number.

*Parent: HLFR-00090, HLFR-00005*

### LLFR-00403 Names a format cannot store
The app must change each signal name that the chosen format cannot store into a valid name, as in LLFR-00543, LLFR-00544, LLFR-00545, LLFR-00546, LLFR-00547, LLFR-00548, LLFR-00549, LLFR-00550, LLFR-00551, LLFR-00552, LLFR-00553 and LLFR-00554. Every change is listed in the box of LLFR-00404.

*Parent: HLFR-00090*

### LLFR-00543 Characters of a MAT name
When the chosen format is MAT, every character of a signal name that is not an English letter, a digit or `_` must be replaced by `_`.

*Parent: HLFR-00090*

### LLFR-00544 Start of a MAT name
When the chosen format is MAT, a signal name that does not start with a letter must get `x` added at its start.

*Parent: HLFR-00090*

### LLFR-00545 Length of a MAT name
When the chosen format is MAT, a signal name longer than 63 characters must be cut to 63 characters.

*Parent: HLFR-00090*

### LLFR-00546 Parts of an HDF5 name
When the chosen format is HDF5, empty parts between `/` characters, parts that are `.` or `..`, and a `/` at the start or end of a signal name must be removed.

*Parent: HLFR-00090*

### LLFR-00547 Empty HDF5 name
When the chosen format is HDF5, a signal name left empty by LLFR-00546 must become `signal`.

*Parent: HLFR-00090*

### LLFR-00548 HDF5 name that is a group
When the chosen format is HDF5, a signal name that is also the group of another saved name (for example `engine` with `engine/speed`) must get an underscore and the smallest number from 2 up that makes it neither a group nor the name of another saved signal.

*Parent: HLFR-00090*

### LLFR-00549 HDF5 name in the group Time
When the chosen format is HDF5, because the time signal is the dataset `Time` (LLFR-00407), a signal name whose first part is the group `Time` (for example `Time/x`) must get an underscore and the smallest number from 2 up on that first part that makes it different from the first parts of the other saved names (for example `Time_2/x`).

*Parent: HLFR-00090*

### LLFR-00550 Blank characters of a CSV or Excel name
When the chosen format is CSV or Excel, spaces and other blank characters at the start and end of a signal name must be removed, because the app removes them when it reads the names (LLFR-00451).

*Parent: HLFR-00090*

### LLFR-00551 Empty CSV or Excel name
When the chosen format is CSV or Excel, a signal name left empty by LLFR-00550 must become `signal`.

*Parent: HLFR-00090*

### LLFR-00552 Changed name already in use
When a name changed as in LLFR-00543, LLFR-00544, LLFR-00545, LLFR-00546, LLFR-00547, LLFR-00548, LLFR-00549, LLFR-00550 or LLFR-00551 is the name of another saved signal, the app must add an underscore and the smallest number from 2 up that makes it unique, as in LLFR-00241, except as in LLFR-00553.

*Parent: HLFR-00090*

### LLFR-00553 MAT name length after a number
When the app adds a number to a MAT name (LLFR-00552), it must still keep the name within 63 characters.

*Parent: HLFR-00090*

### LLFR-00554 No other change of CSV and Excel names
CSV and Excel names must not be changed otherwise than as in LLFR-00550, LLFR-00551 and LLFR-00552, except as in LLFR-00407 and LLFR-00557.

*Parent: HLFR-00090*

### LLFR-00404 Changed names after saving
After saving the file, if any name was changed (LLFR-00941, LLFR-00960, LLFR-00403, LLFR-00407, LLFR-00557), including the name of the time signal, the app must show one information box that lists each changed name as `<name in the app> → <new name>`, for example `file1_Speed → Speed_1` and `file2_Speed → Speed_2`.

Note: The box is an information box, not an error box (HLFR-00002). The removal of the prefix alone (LLFR-00940) is not listed, because it applies to every signal, so `file1_Accel → Accel` does not appear.

*Parent: HLFR-00090*

### LLFR-00885 Scrollable changed names box
The information box of LLFR-00404 must be scrollable when its list is longer than the box can show.

*Parent: HLFR-00090*

### LLFR-00555 No message when no name changed
After saving the file, if no name was changed (LLFR-00941, LLFR-00960, LLFR-00403, LLFR-00407, LLFR-00557), the app must not show any message.

*Parent: HLFR-00090*

### LLFR-00405 Saving changes nothing in the app
Saving the signals must not change the signal list, the names of the signals in the app, the plots, the open data files or the undo and redo history.

*Parent: HLFR-00090, HLFR-00040*

### LLFR-00556 Saving the signals not undoable
Saving the signals must not be an undoable action (LLFR-00140).

*Parent: HLFR-00090, HLFR-00040*

### LLFR-00407 Time signal name in a saved file
The app must write the time signal of LLFR-00939 (HLFR-00006, LLFR-00326) under the name `Time`, in every format, so that opening the saved file finds its time signal by its name (LLFR-00053) and does not show the time signal window (LLFR-00325).

*Parent: HLFR-00090, HLFR-00006*

### LLFR-00557 Other names that match the time signal name
Every saved signal other than the time signal (LLFR-00407) whose name, after LLFR-00940, LLFR-00941, LLFR-00960 and LLFR-00403, would also match the time signal name in the chosen format (LLFR-00053, LLFR-00330), for example `TIME` or `time`, must get an underscore and the smallest number from 2 up that makes its name unique, as in LLFR-00241, for example `TIME_2`, so that the saved file has only one signal that matches the time signal name.

Note: Such other names exist, for example, when a data file holds both `Time` and `TIME` (LLFR-00324), or when a synthetic signal was renamed `time` (LLFR-00266). A time signal chosen in the window (LLFR-00326) has no other signal of the data file matching the time signal name.

*Parent: HLFR-00090, HLFR-00006*

### LLFR-00558 Time signal rename in the box
When the plain name (LLFR-00940) of the saved time signal (LLFR-00939) is not exactly `Time`, its change to `Time` (LLFR-00407) must be listed in the box of LLFR-00404 like the other changed names, for example `file1_t → Time`.

*Parent: HLFR-00090, HLFR-00006*

### LLFR-00408 Signals with values that are not numbers
If any signal to save (LLFR-00401) has a sample that is not a finite number (infinite or NaN), for example a synthetic signal whose values overflowed, the app must not write the file, because no data file the app opens can hold such values (LLFR-00065).

*Parent: HLFR-00090*

### LLFR-00559 Error box for values that are not numbers
If any signal to save (LLFR-00401) has a sample that is not a finite number (LLFR-00408), the app must show an error box saying that the signals could not be saved because these signals have values that are not finite numbers, naming each of them.

*Parent: HLFR-00090, HLFR-00002*

### LLFR-00418 Loading indication
While the app reads and checks a selected file (LLFR-00328, step 3), whether or not other data files are open, it must show the mouse pointer as a busy pointer over the app window.

*Parent: HLFR-00004, HLFR-00117*

### LLFR-00560 Loading title
While the app reads and checks a selected file (LLFR-00328, step 3), whether or not other data files are open, the title of the main window must be "plot_tool (loading)".

*Parent: HLFR-00004, HLFR-00117*

### LLFR-00561 Normal pointer after loading
As soon as reading and checking end (LLFR-00418), whether the file can be opened or not, and before the app shows a File Open Error box or the window of LLFR-00325, the app must restore the normal mouse pointer.

*Parent: HLFR-00004*

### LLFR-00562 Normal title after loading
As soon as reading and checking end (LLFR-00560), whether the file can be opened or not, and before the app shows a File Open Error box or the window of LLFR-00325, the app must set the title of the main window back to the normal title "plot_tool".

*Parent: HLFR-00004*

### LLFR-00563 Normal title otherwise
The title of the main window must be the normal title "plot_tool" the rest of the time, outside the reading and checking of LLFR-00560.

*Parent: HLFR-00004*

### LLFR-00564 DELETED
DELETED

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
The signal list panel must include the time signal of each open data file (HLFR-00006) among the signal names it shows.

*Parent: HLFR-00011, HLFR-00006*

### LLFR-00055 Plotting the time signal
The app must let the user plot the time signal of each data file (HLFR-00006) in the same ways as any other signal.

*Parent: HLFR-00012, HLFR-00013*

### LLFR-00056 Drop a signal already in the plot
If the user drops a signal name on a plot that already shows that signal, the app must not draw the signal again.

*Parent: HLFR-00013*

### LLFR-00057 No message on duplicate drop
If the user drops a signal name on a plot that already shows that signal, the app must not show any message.

*Parent: HLFR-00013*

### LLFR-00094 Search box
The signal list panel must contain a search box placed directly below the signal list, with nothing between them.

*Parent: HLFR-00033*

### LLFR-00095 Filter while typing
Each time the text in the search box changes, the app must show in the signal list only the signals that match the text (LLFR-00098 to LLFR-00101, LLFR-00566, LLFR-00105 and LLFR-00567).

*Parent: HLFR-00033*

### LLFR-00096 Empty search
When the search box is empty or contains only spaces, the signal list must show all the signals of the open data files, with their synthetic signals.

*Parent: HLFR-00033*

### LLFR-00097 No matching signals
When no signal of an open data file matches the text in the search box, the signal list must show the text "No matching signals" below the file name row of that file (LLFR-00362).

*Parent: HLFR-00033*

### LLFR-00565 No signals shown when nothing matches
When no signal matches the text in the search box, the signal list must show no signals.

*Parent: HLFR-00033*

### LLFR-00098 Case-insensitive search
The search must ignore the difference between uppercase and lowercase letters.

*Parent: HLFR-00034*

### LLFR-00099 Partial-name search
A search word (LLFR-00105) must match a signal when it appears anywhere in the signal's name.

*Parent: HLFR-00034*

### LLFR-00100 Separators ignored in the typed text
The search must ignore underscores (`_`), hyphens (`-`) and dots (`.`) in the typed text.

*Parent: HLFR-00034*

### LLFR-00566 Separators ignored in the signal names
The search must ignore spaces, underscores, hyphens and dots in the signal names.

Note: For example, `enginespeed` finds `Engine_Speed`.

*Parent: HLFR-00034*

### LLFR-00101 Typo-tolerant search
When a search word (LLFR-00105), after LLFR-00098 and LLFR-00100 are applied, has 4 or more characters, it must also match a signal whose name contains a part that differs from the word by at most one wrong, missing or extra character for every full 4 characters of the word (1 for 4 to 7 characters, 2 for 8 to 11 characters, and so on).

Note: For example, `presure` finds `Pressure`, and `sine_2hz` finds `Sine_3Hz`.

*Parent: HLFR-00034*

### LLFR-00102 Order of search results
Below the file name row of each open data file, the app must list the matching signals of that file, which are the signals whose name contains every search word, exactly or within the typo allowance of LLFR-00101 (LLFR-00105, LLFR-00567), in three groups in this order, keeping the order of the signal list (LLFR-00934) within each group:
1. the signals that match every search word without LLFR-00101 and whose name, after LLFR-00098, LLFR-00100 and LLFR-00566 are applied, starts with the first search word, once its prefix of LLFR-00900 is left out;
2. the other signals that match every search word without LLFR-00101;
3. the signals that need LLFR-00101 for at least one search word.

*Parent: HLFR-00034, HLFR-00113*

### LLFR-00103 Plotting from search results
The user must be able to plot the signals shown in a filtered signal list in the same ways as in the full list (LLFR-00019, LLFR-00021).

*Parent: HLFR-00033, HLFR-00012, HLFR-00013*

### LLFR-00104 Search cleared on file open
When the app opens a data file (LLFR-00915), it must clear the search box.

*Parent: HLFR-00033, HLFR-00117*

### LLFR-00105 Multi-word search
The app must split the typed text into search words at each space.

Note: For example, with the signals `mateus_soares_rodrigues 2026` and `mateus_soares_rodrigues 2025`, typing `mate so 25` finds only `mateus_soares_rodrigues 2025`.

*Parent: HLFR-00034*

### LLFR-00567 Every search word must match
A signal must match the search only when every search word (LLFR-00105) matches its name (LLFR-00098 to LLFR-00101 and LLFR-00566), in any order.

Note: For example, with the signals `mateus_soares_rodrigues 2026` and `mateus_soares_rodrigues 2025`, typing `mate so 25` finds only `mateus_soares_rodrigues 2025`.

*Parent: HLFR-00034*

### LLFR-00900 Signal name prefix
The app must name each signal of a data file with `file`, the file's number (LLFR-00895), `_` and the signal's name in the file, for example `file1_Speed` for the signal `Speed` of file 1.

*Parent: HLFR-00115*

### LLFR-00901 Prefix with one file open
The app must add the prefix of LLFR-00900 also while only one data file is open.

*Parent: HLFR-00115*

### LLFR-00902 Prefixed name used everywhere
The app must use the name of LLFR-00900 as the signal's name wherever it shows or saves the name of a signal, for example in the signal list, the legends, the menu titles (LLFR-00426), the search (LLFR-00095), the second signal dialog (LLFR-00275) and the layout files (LLFR-00943), except as in LLFR-00905 and LLFR-00940.

*Parent: HLFR-00115*

### LLFR-00903 Synthetic signal name starts with the file prefix
The app must name a synthetic signal with the prefix of its data file (LLFR-00900, LLFR-00935), followed by the name of LLFR-00240, which is built from the names without their prefix of the signals it was computed from, except as in LLFR-00953.

Note: For example, the Integral of `file1_Speed` is `file1_int_Speed`, a Low-pass filter of `file1_Speed` is `file1_lpf_2Hz_order2_Speed`, its Integral is `file1_int_lpf_2Hz_order2_Speed`, and the FFT of `file1_Speed` is `file1_fft_1p5s_to_3s_Speed`.

*Parent: HLFR-00115, HLFR-00054, HLFR-00104*

### LLFR-00953 Second signal of another file in a product name
When the second signal of a Product with signal (LLFR-00275) belongs to another data file than the right-clicked signal, the app must write the name of the second signal in the product's name (LLFR-00240) with its own prefix (LLFR-00900).

Note: For example, `file1_Speed_prod_Torque` for two signals of file 1, and `file1_Speed_prod_file2_Torque` when `Torque` belongs to file 2.

*Parent: HLFR-00115, HLFR-00104*

### LLFR-00954 Prefix kept on a rename
When the user renames a synthetic signal (LLFR-00266), the app must keep the prefix of its data file (LLFR-00935) in front of the name the user types, so that the user types only the part after the prefix.

Note: For example, typing `my` for a synthetic signal of file 1 gives `file1_my`. The empty-name check of LLFR-00267 and LLFR-00607 applies to the typed part; the name-in-use check of LLFR-00267 and LLFR-00606 applies to the whole name.

*Parent: HLFR-00115, HLFR-00060*

### LLFR-00904 Time signal found by its name in the file
The app must match the time signal name (LLFR-00053, LLFR-00324, LLFR-00330) against each signal's name in its file, before the prefix of LLFR-00900 is added.

Note: A signal named `Time` in file 1 is therefore the time signal of file 1 and is shown as `file1_Time`.

*Parent: HLFR-00006, HLFR-00115*

### LLFR-00905 Plain names in the time signal window
The window of LLFR-00325 must list the signals of the file being opened with their names in the file, without the prefix of LLFR-00900.

*Parent: HLFR-00070, HLFR-00115*

### LLFR-00952 File named in the time signal window
The window of LLFR-00325 must show the name of the file it is for, with its extension and without its folder.

Note: With several files selected (LLFR-00946), each file that needs it gets its own window.

*Parent: HLFR-00070, HLFR-00122*

### LLFR-00239 Synthetic signal menu
When the user right-clicks a signal name in the signal list panel, the app must show a menu with a "Create synthetic signal" option that lists the operations of LLFR-00268, showing only these operation names and not the names the new signals will have (LLFR-00240).

*Parent: HLFR-00053*

### LLFR-00568 Choosing an operation
When the user chooses an operation in the "Create synthetic signal" option (LLFR-00239), the app must create the synthetic signal of that operation from the right-clicked signal.

*Parent: HLFR-00053*

### LLFR-00240 Synthetic signal names
After the prefix of its data file (LLFR-00903), the app must name a synthetic signal as follows, using the abbreviation of its operation (LLFR-00268) and the full current name, without its prefix (LLFR-00900), of each signal it was computed from, except as in LLFR-00953:

| Operation | Name | Example |
|---|---|---|
| Integral, Derivative, Max, Min, Absolute value | `<abbreviation>_<signal>` | `file1_int_Speed`, `file1_abs_Speed` |
| Add, Subtract, Multiply and Divide by constant | `<abbreviation>_<constant>_<signal>` | `file1_add_2p5_Speed`, `file1_sub_2n0_Speed` |
| Greater than, Less than, Greater than or equal, Less than or equal | `<abbreviation>_<constant>_<signal>` | `file1_gt_2p5_Speed` |
| Low-pass filter, High-pass filter | `<abbreviation>_<cutoff>Hz_order<order>_<signal>` | `file1_lpf_0p5Hz_order2_Speed` |
| Moving average | `mavg_<window>samples_<signal>` | `file1_mavg_10samples_Speed` |
| FFT | `fft_<start>s_to_<end>s_<signal>` | `file1_fft_1p5s_to_3s_Speed` |
| Product with signal | `<right-clicked signal>_prod_<second signal>` (LLFR-00275) | `file1_Speed_prod_Torque`; with `Torque` of file 2, `file1_Speed_prod_file2_Torque` (LLFR-00953) |

The FFT times are the time range of LLFR-00963 and LLFR-00592, so two FFTs of the same signal over different time ranges get different names. When a signal it was computed from is itself a synthetic signal, its whole name without its prefix is used, so that the names build up from left to right, for example `file1_der_int_Speed` or `file1_fft_1p5s_to_3s_lpf_0p5Hz_order2_Speed`.

*Parent: HLFR-00054, HLFR-00104, HLFR-00115*

### LLFR-00569 Numbers in synthetic signal names
Every number in the name of a synthetic signal (LLFR-00240), which is the constant, the cutoff frequency, the filter order, the window size or an FFT time, must be written with letters and digits only, with the same significant digits as the data tip's values (LLFR-00043, LLFR-00044), up to 6, as in LLFR-00570, LLFR-00571, LLFR-00572, LLFR-00573, LLFR-00574, LLFR-00575 and LLFR-00576. The name of a synthetic signal therefore holds only letters, digits and `_` apart from the names of the signals it was computed from.

*Parent: HLFR-00054*

### LLFR-00570 Decimal point in a name number
In a number of a synthetic signal name (LLFR-00569), the decimal point must be written `p` for a positive number and `n` for a negative number: 2.5 is `2p5`, -2.5 is `2n5` and -0.000123457 is `0n000123457`.

*Parent: HLFR-00054*

### LLFR-00571 No minus sign in a name number
In a number of a synthetic signal name (LLFR-00569), a negative number must have no minus sign: -2.5 is `2n5` and -0.000123457 is `0n000123457`.

*Parent: HLFR-00054*

### LLFR-00572 Positive whole number in a name
In a number of a synthetic signal name (LLFR-00569), a positive whole number must be written as it is: 2 is `2`.

*Parent: HLFR-00054*

### LLFR-00573 Negative whole number in a name
In a number of a synthetic signal name (LLFR-00569), a negative whole number must get `n0`: -2 is `2n0`.

*Parent: HLFR-00054*

### LLFR-00574 No exponent in a name number
In a number of a synthetic signal name (LLFR-00569), no exponent must be used: 1e+06 is `1000000` and 1e-07 is `0p0000001`.

*Parent: HLFR-00054*

### LLFR-00575 All digits in a name number
In a number of a synthetic signal name (LLFR-00569), all digits must be written, rounded to the significant digits of LLFR-00569: 1e+06 is `1000000`, 1e-07 is `0p0000001` and 1234567 is `1234570`.

*Parent: HLFR-00054*

### LLFR-00576 Zero in a name
In a number of a synthetic signal name (LLFR-00569), zero must be written `0`.

*Parent: HLFR-00054*

### LLFR-00577 Filter start not in the name
How a filter starts (LLFR-00588, LLFR-00589) must not be part of the name of a synthetic signal (LLFR-00240).

*Parent: HLFR-00054*

### LLFR-00264 Synthetic signals from synthetic signals
The app must let the user create a synthetic signal from a synthetic signal in the same way as from a signal of a data file (LLFR-00239, LLFR-00568), except as in LLFR-00251.

*Parent: HLFR-00053*

### LLFR-00241 Synthetic signal name already used
If the name of LLFR-00240 is already the name of a signal in the signal list, the app must add an underscore and the smallest number from 2 up that makes the name unique, for example `file1_lpf_0p5Hz_order2_Speed_2`.

Note: This happens, for example, when the same signal is filtered twice with the same cutoff frequency and order but different starts (LLFR-00588, LLFR-00589).

*Parent: HLFR-00054*

### LLFR-00242 Synthetic signals in the signal list
The signal list panel must show the synthetic signals of each data file (LLFR-00935) after the signals of that file, in the order they were created, in italic letters.

*Parent: HLFR-00053, HLFR-00011, HLFR-00113*

### LLFR-00935 File of a synthetic signal
Each synthetic signal must belong to the data file of the signal it was computed from, which for a Product with signal is the data file of the right-clicked signal.

Note: The second signal of a Product with signal can belong to another data file only when its time signal is exactly the same (LLFR-00275), so the product is computed on that one time signal. Closing either file removes the product, because it is computed from a signal of that file (LLFR-00921).

*Parent: HLFR-00053, HLFR-00113*

### LLFR-00936 Synthetic signals use the time of their file
The app must compute each synthetic signal with the time signal of its file (LLFR-00935) wherever its operation uses the time signal or the time samples (LLFR-00243, LLFR-00244, LLFR-00580, LLFR-00247, LLFR-00248, LLFR-00271).

*Parent: HLFR-00053, HLFR-00116*

### LLFR-00963 FFT time range of a signal
When at least one time plot exists when the user chooses "FFT", the app must take as the time range of the FFT the part of the x-axis range shared by the time plots (LLFR-00070) that lies within the time range of the signal's data file (LLFR-00935).

Note: The FFT name shows this range (LLFR-00240). With no time plot, the FFT uses all the samples (LLFR-00592).

*Parent: HLFR-00057, HLFR-00113*

### LLFR-00964 Too few samples of the signal in the shown range
When the user chooses "FFT", at least one time plot exists and the time range of LLFR-00963 holds fewer than 8 samples of the signal, the app must show an information box saying that the shown x-axis range does not hold enough samples of the signal to compute an FFT, and asking the user to move the x-axis to a range where the signal has samples.

Note: The FFT is then not created (LLFR-00250). This includes a range that does not overlap the signal's file at all.

*Parent: HLFR-00057, HLFR-00053, HLFR-00113*

### LLFR-00962 One list in the second signal dialog
The dialog of LLFR-00275 must show its signals in one flat list, in the order of the signal list (LLFR-00933, LLFR-00934), with the names of LLFR-00900 and with no file name row.

*Parent: HLFR-00053, HLFR-00113*

### LLFR-00578 Search for synthetic signals
The user must be able to search for the synthetic signals (HLFR-00033) like the signals of the data files.

*Parent: HLFR-00053, HLFR-00011*

### LLFR-00579 Plot synthetic signals
The user must be able to plot the synthetic signals (LLFR-00019, LLFR-00021) like the signals of the data files, except as in LLFR-00257.

*Parent: HLFR-00053, HLFR-00011*

### LLFR-00243 Integral
The Integral of a signal must have, at each time sample, the integral of the signal over time from the first time sample up to that sample, computed with the trapezoidal rule, so that its first sample is 0.

*Parent: HLFR-00053*

### LLFR-00244 Derivative
The Derivative of a signal must have, at each time sample other than the first and the last, the rate of change of the signal with respect to time, computed from the neighboring samples on both sides.

*Parent: HLFR-00053*

### LLFR-00580 Derivative at the ends
The Derivative of a signal (LLFR-00244) must have, at the first and last samples, the rate of change of the signal with respect to time, computed from the one neighbor.

*Parent: HLFR-00053*

### LLFR-00245 Filter dialog
When the user chooses "Low-pass filter" or "High-pass filter" (LLFR-00239), the app must show a dialog that asks for the cutoff frequency in Hz and for the filter order, and states both allowed ranges: for the cutoff frequency, greater than 0 and less than half the sampling rate (LLFR-00247); for the order, a whole number from 1 to 8.

*Parent: HLFR-00053*

### LLFR-00581 Starting filter order
The dialog of LLFR-00245 must show 2 as the starting value of the order.

*Parent: HLFR-00053*

### LLFR-00582 Filter start choice
The dialog of LLFR-00245 must also let the user choose how the filter starts (LLFR-00588, LLFR-00589), with two choices, "From the first value" and "From zero".

*Parent: HLFR-00053*

### LLFR-00583 Starting filter start choice
In the dialog of LLFR-00245, "From the first value" must be chosen when the dialog opens (LLFR-00582).

*Parent: HLFR-00053*

### LLFR-00584 Filter created only from allowed values
The app must create the filtered signal of LLFR-00245 only when the user confirms a cutoff frequency and an order in their allowed ranges.

*Parent: HLFR-00053*

### LLFR-00585 Filter dialog stays open
If a value in the dialog of LLFR-00245 is outside its range or not a number, the dialog must stay open.

*Parent: HLFR-00053*

### LLFR-00586 Filter dialog says why
If a value in the dialog of LLFR-00245 is outside its range or not a number, the dialog must say why.

*Parent: HLFR-00053*

### LLFR-00587 Filter dialog cancelled
If the user cancels the dialog of LLFR-00245, the app must not create any signal.

*Parent: HLFR-00053*

### LLFR-00246 Filter type
The Low-pass filter and the High-pass filter must be Butterworth filters of the order of LLFR-00245, with its cutoff frequency, applied once over the signal, forward in time, as a real-time filter would be, so that the filtered curve is delayed like the output of a real filter.

*Parent: HLFR-00053*

### LLFR-00588 Filter start from the first value
When the user chose "From the first value" in the dialog of LLFR-00245 (LLFR-00582), the Low-pass filter and the High-pass filter (LLFR-00246) must start as if the signal had kept the value of its first sample before the first sample (steady-state initial conditions), so that the filtered curve starts in sync with the first value and does not jump at the start.

Note: With "From the first value", a constant signal stays unchanged through a Low-pass filter and gives 0 through a High-pass filter, from the first sample on.

*Parent: HLFR-00053*

### LLFR-00589 Filter start from zero
When the user chose "From zero" in the dialog of LLFR-00245 (LLFR-00582), the Low-pass filter and the High-pass filter (LLFR-00246) must start at rest (zero initial state), as if the signal had been 0 before the first sample, like a real filter switched on at the first sample, so that the filtered curve settles after the start.

Note: With "From zero", a constant signal gives a Low-pass output that starts below the constant and rises towards it, and a High-pass output that starts at a part of the constant (close to it when the cutoff frequency is well below half the sampling rate) and decays towards 0.

*Parent: HLFR-00053*

### LLFR-00247 Sampling rate
The app must compute the sampling rate as 1 divided by the mean time step of the time signal of the right-clicked signal's data file (LLFR-00935).

*Parent: HLFR-00053*

### LLFR-00590 Evenly spaced time samples
When the user chooses "Low-pass filter", "High-pass filter" or "FFT" and any time step differs from the mean time step (LLFR-00247) by more than 1%, the app must not create the signal.

*Parent: HLFR-00053*

### LLFR-00591 Uneven time samples message
When the user chooses "Low-pass filter", "High-pass filter" or "FFT" and any time step differs from the mean time step (LLFR-00247) by more than 1%, the app must show an information box saying that the operation needs evenly spaced time samples.

*Parent: HLFR-00053*

### LLFR-00248 FFT time range
When at least one time plot exists, the FFT must use only the samples of the signal whose time is within the time range of LLFR-00963, taken when the FFT is created.

*Parent: HLFR-00057, HLFR-00113*

### LLFR-00592 FFT without a time plot
When no time plot exists when the FFT is created, the FFT must use all samples of the signal.

*Parent: HLFR-00057*

### LLFR-00593 FFT fixed after creation
A change of the time range after an FFT signal is created (LLFR-00248, LLFR-00592) must not change the FFT signal.

*Parent: HLFR-00057*

### LLFR-00249 FFT result
The FFT signal must be the one-sided amplitude spectrum of the samples of LLFR-00248 and LLFR-00592, from 0 Hz up to half the sampling rate (LLFR-00247), computed with a Hann window and scaled so that a sine wave of amplitude A over the whole time range gives a peak of height close to A.

*Parent: HLFR-00053, HLFR-00057*

### LLFR-00250 Too few samples for an FFT
When the user chooses "FFT" and fewer than 8 samples of the signal are within the time range of LLFR-00248 and LLFR-00592, the app must not create the FFT signal.

*Parent: HLFR-00053, HLFR-00057*

### LLFR-00594 Too few samples message
When the user chooses "FFT" and fewer than 8 samples of the signal are within the time range of LLFR-00248 and LLFR-00592, the app must show an information box saying that the time range holds too few samples, except as in LLFR-00964.

*Parent: HLFR-00053, HLFR-00057*

### LLFR-00251 No operations on FFT signals
When the user right-clicks an FFT signal, the app must show the "Create synthetic signal" option (LLFR-00239) as disabled.

Note: An FFT signal has frequency, not time, on its x-axis, so the operations do not apply to it.

*Parent: HLFR-00053*

### LLFR-00252 DELETED
DELETED

### LLFR-00253 Data files unchanged
The app must never write synthetic signals, or anything else, to a data file.

Note: The Save signals button writes them to a new file, never to a data file (LLFR-00397, LLFR-00401).

*Parent: HLFR-00105*

### LLFR-00595 Synthetic signals only in memory
Synthetic signals must exist only in the app's memory, until they are deleted (LLFR-00255, LLFR-00597), their data file is closed (LLFR-00921, LLFR-00931) or the app is closed.

Note: A layout file can create them again (LLFR-00262), except the FFT signals (LLFR-00283).

*Parent: HLFR-00055*

### LLFR-00254 Delete synthetic signal option
When the user right-clicks a synthetic signal in the signal list panel, the app must show a "Delete signal" option in the menu of LLFR-00239.

*Parent: HLFR-00059*

### LLFR-00596 No Delete signal option for data file signals
The menu of LLFR-00239 of a signal of a data file must not have the "Delete signal" option (LLFR-00254).

*Parent: HLFR-00059*

### LLFR-00255 Delete synthetic signal action
When the user chooses "Delete signal" (LLFR-00254), the app must ask the user whether to proceed, naming the synthetic signals that were computed from it, directly or through other synthetic signals.

*Parent: HLFR-00059*

### LLFR-00597 Deleted signals leave the list
If the user proceeds in the question of LLFR-00255, the app must remove the signal and the synthetic signals named in the question from the signal list.

*Parent: HLFR-00059*

### LLFR-00598 Curves of deleted signals removed
If the user proceeds in the question of LLFR-00255, the app must remove the curves of the signal and of the synthetic signals named in the question from every plot (deleting each plot left with no curve as in LLFR-00051).

*Parent: HLFR-00059*

### LLFR-00599 History cleared on signal delete
If the user proceeds in the question of LLFR-00255, the app must clear the undo and redo history.

Note: Creating and deleting a synthetic signal are not undoable actions (LLFR-00140).

*Parent: HLFR-00059*

### LLFR-00263 Removing a synthetic curve keeps the signal
When the user removes the curve of a synthetic signal from a plot (LLFR-00039), or deletes a plot or tab that holds it (LLFR-00049, LLFR-00028), the app must keep the synthetic signal in the signal list.

*Parent: HLFR-00059, HLFR-00022*

### LLFR-00600 Only Delete signal removes a synthetic signal
Only "Delete signal" (LLFR-00255, LLFR-00597) must remove a synthetic signal from the list.

*Parent: HLFR-00059, HLFR-00022*

### LLFR-00265 Rename synthetic signal option
When the user right-clicks a synthetic signal in the signal list panel, the app must show a "Rename" option in the menu of LLFR-00239.

*Parent: HLFR-00060*

### LLFR-00601 No Rename option for data file signals
The menu of LLFR-00239 of a signal of a data file must not have the "Rename" option (LLFR-00265).

*Parent: HLFR-00060*

### LLFR-00266 Rename synthetic signal action
When the user chooses "Rename" (LLFR-00265), the app must let the user type a new name for the synthetic signal.

Note: Renaming a synthetic signal is not an undoable action (LLFR-00140) and does not clear the undo and redo history.

*Parent: HLFR-00060*

### LLFR-00602 New name in the signal list
After the user types a new name for a synthetic signal (LLFR-00266), the app must show the new name in the signal list.

*Parent: HLFR-00060*

### LLFR-00603 New name in the legends
After the user types a new name for a synthetic signal (LLFR-00266), the app must show the new name in the legend of every plot that draws the signal.

*Parent: HLFR-00060*

### LLFR-00604 Names of dependent signals kept
When a synthetic signal is renamed (LLFR-00266), the names of synthetic signals already computed from it must not change.

*Parent: HLFR-00060*

### LLFR-00605 Later signals use the new name
Synthetic signals created from a renamed synthetic signal (LLFR-00266) after the rename must use the new name (LLFR-00240).

*Parent: HLFR-00060*

### LLFR-00267 Invalid synthetic signal name
If the user enters a name that, without leading and trailing spaces, is empty or is the name of another signal in the signal list, the app must keep the previous name.

*Parent: HLFR-00060*

### LLFR-00606 Synthetic signal name already in use
If the user enters a name (LLFR-00266) that, without leading and trailing spaces, is the name of another signal in the signal list, the app must show an information box saying that a signal with that name already exists.

*Parent: HLFR-00060*

### LLFR-00607 Empty synthetic signal name
If the user enters a name (LLFR-00266) that, without leading and trailing spaces, is empty, the app must not show any message.

*Parent: HLFR-00060*

### LLFR-00268 Synthetic operation groups
The "Create synthetic signal" option (LLFR-00239) must list the operations in these groups, in this order:
1. Calculus: "Integral (int)", "Derivative (der)";
2. Filters: "Low-pass filter (lpf)", "High-pass filter (hpf)", "Moving average (mavg)";
3. Statistics: "Max (max)", "Min (min)";
4. Comparison: "Greater than (gt)", "Less than (lt)", "Greater than or equal (ge)", "Less than or equal (le)";
5. Arithmetic: "Add constant (add)", "Subtract constant (sub)", "Multiply by constant (mul)", "Divide by constant (div)", "Absolute value (abs)", "Product with signal (prod)";
6. Spectrum: "FFT (fft)".

The text in parentheses is the operation's abbreviation, which the app uses in the names of the synthetic signals (LLFR-00240).

*Parent: HLFR-00053*

### LLFR-00269 Moving average window dialog
When the user chooses "Moving average", the app must show a dialog that asks for the window size as a whole number of samples and states the allowed range: from 2 up to the number of samples of the signal.

*Parent: HLFR-00053*

### LLFR-00608 Moving average created only from allowed values
The app must create the Moving average signal of LLFR-00269 only when the user confirms a value in the allowed range.

*Parent: HLFR-00053*

### LLFR-00609 Window dialog stays open
If the value in the dialog of LLFR-00269 is outside the range or not a whole number, the dialog must stay open.

*Parent: HLFR-00053*

### LLFR-00610 Window dialog says why
If the value in the dialog of LLFR-00269 is outside the range or not a whole number, the dialog must say why.

*Parent: HLFR-00053*

### LLFR-00611 Window dialog cancelled
If the user cancels the dialog of LLFR-00269, the app must not create any signal.

*Parent: HLFR-00053*

### LLFR-00270 Moving average
The Moving average of a signal must have, at each time sample, the mean of the window of LLFR-00269 centered on that sample, with one more sample after it than before it when the window size is even.

*Parent: HLFR-00053*

### LLFR-00612 Moving average near the ends
Near the first and last samples, the window of the Moving average (LLFR-00270) must hold only the samples that exist.

*Parent: HLFR-00053*

### LLFR-00271 Max and Min
The Max and the Min of a signal must be constant signals, with at every time sample the largest and the smallest value, respectively, of all samples of the signal over the whole time range of its data file (LLFR-00935), whatever time range the plots show.

*Parent: HLFR-00053*

### LLFR-00272 Constant value dialog
When the user chooses a Comparison or an Arithmetic operation other than "Absolute value" and "Product with signal" (LLFR-00268), the app must show a dialog that asks for a constant number.

*Parent: HLFR-00053*

### LLFR-00613 Constant signal created only from allowed values
The app must create the signal of LLFR-00272 only when the user confirms a number, other than 0 for "Divide by constant".

*Parent: HLFR-00053*

### LLFR-00614 Constant dialog stays open
If the value in the dialog of LLFR-00272 is not a number, or is 0 for "Divide by constant", the dialog must stay open.

*Parent: HLFR-00053*

### LLFR-00615 Constant dialog says why
If the value in the dialog of LLFR-00272 is not a number, or is 0 for "Divide by constant", the dialog must say why.

*Parent: HLFR-00053*

### LLFR-00616 Constant dialog cancelled
If the user cancels the dialog of LLFR-00272, the app must not create any signal.

*Parent: HLFR-00053*

### LLFR-00273 Comparison operations
A Comparison signal must have, at each time sample, the value 1 when the signal's sample is greater than ("Greater than"), less than ("Less than"), greater than or equal to ("Greater than or equal") or less than or equal to ("Less than or equal") the constant of LLFR-00272, and the value 0 otherwise.

*Parent: HLFR-00053*

### LLFR-00274 Arithmetic with a constant
An "Add constant", "Subtract constant", "Multiply by constant" or "Divide by constant" signal must have, at each time sample, the signal's sample plus, minus, multiplied by or divided by the constant of LLFR-00272, respectively.

*Parent: HLFR-00053*

### LLFR-00275 Second signal dialog
When the user chooses "Product with signal", the app must show a dialog that lists every signal and every synthetic signal (LLFR-00935) of the right-clicked signal's data file and of every other open data file whose time signal has the same number of samples and exactly the same value at every sample, except the FFT signals, including the right-clicked signal, in one list (LLFR-00962), in which the user chooses the second signal.

*Parent: HLFR-00053, HLFR-00113*

### LLFR-00617 Second signal dialog cancelled
If the user cancels the dialog of LLFR-00275, the app must not create any signal.

*Parent: HLFR-00053*

### LLFR-00276 Product with signal
The Product of two signals must have, at each time sample, the sample of the right-clicked signal multiplied by the sample of the second signal (LLFR-00275) at the same time sample.

*Parent: HLFR-00053*

### LLFR-00284 Absolute value
The Absolute value of a signal must have, at each time sample, the absolute value of the signal's sample.

*Parent: HLFR-00053*

### LLFR-00285 Search in the second signal dialog
The dialog of LLFR-00275 must contain a search box above its list of signals.

Note: The search box is a text field (LLFR-00157), so typing in it never activates a plot tool, undoes or redoes (LLFR-00195, LLFR-00196).

*Parent: HLFR-00053, HLFR-00034*

### LLFR-00618 Second signal dialog filter
Each time the text in the search box of LLFR-00285 changes, the dialog must show in its one list (LLFR-00962) only the signals that match the text by the rules of the signal list search (LLFR-00095, LLFR-00098 to LLFR-00101, LLFR-00566, LLFR-00105, LLFR-00567), in the three groups of LLFR-00102 formed over the whole list, keeping the order of the list within each group.

*Parent: HLFR-00053, HLFR-00034, HLFR-00113*

### LLFR-00619 Second signal dialog empty search
When the search box of LLFR-00285 is empty or contains only spaces, the dialog must show all its signals (LLFR-00096).

*Parent: HLFR-00053, HLFR-00034*

### LLFR-00620 Second signal dialog with no match
When no signal matches the text in the search box of LLFR-00285, the dialog must show no signals (LLFR-00565).

*Parent: HLFR-00053, HLFR-00034*

### LLFR-00621 Second signal dialog no-match text
When no signal matches the text in the search box of LLFR-00285, the dialog must show the text "No matching signals" (LLFR-00097).

*Parent: HLFR-00053, HLFR-00034*

### LLFR-00622 Second signal dialog focus
When the dialog of LLFR-00275 opens, the keyboard focus must be in its search box (LLFR-00285).

*Parent: HLFR-00053, HLFR-00034*

### LLFR-00277 Copy name option
When the user right-clicks a signal name in the signal list panel, the app must show a "Copy name" option in the menu of LLFR-00239.

*Parent: HLFR-00061*

### LLFR-00623 Copy name action
When the user chooses "Copy name" (LLFR-00277), the app must put the signal's name on the system clipboard as text.

*Parent: HLFR-00061*

### LLFR-00278 Copy equation option
When the user right-clicks a synthetic signal that is not an FFT signal in the signal list panel, the app must show a "Copy equation" option in the menu of LLFR-00239.

Note: FFT signals are not saved in layout files (LLFR-00283), so they have no equation.

*Parent: HLFR-00062*

### LLFR-00624 No Copy equation option for other signals
The menu of LLFR-00239 of a signal of a data file or of an FFT signal must not have the "Copy equation" option (LLFR-00278).

Note: FFT signals are not saved in layout files (LLFR-00283), so they have no equation.

*Parent: HLFR-00062*

### LLFR-00279 Copy equation action
When the user chooses "Copy equation" (LLFR-00278), the app must put on the system clipboard, as text, the entries that the layout file uses for synthetic signals (LLFR-00225, LLFR-00227) for that synthetic signal, which is not an FFT signal, and for every synthetic signal it is computed from, directly or through other synthetic signals, in the order they were created, written as a JSON list that can be pasted into the list of synthetic signals of a layout file.

*Parent: HLFR-00062, HLFR-00056*

### LLFR-00290 Select signals with the mouse
In the signal list, a click on a signal must select only that signal, except as in LLFR-00625 and LLFR-00626.

*Parent: HLFR-00063*

### LLFR-00625 Click with the Data tip key
In the signal list, a click on a signal with the Data tip key held (LLFR-00148) must add the signal to the selection, or remove it if it is already selected.

*Parent: HLFR-00063*

### LLFR-00626 Click with the Shift key
In the signal list, a click on a signal with the Shift key held must select all the signals shown from the last clicked signal up to the clicked one.

*Parent: HLFR-00063*

### LLFR-00291 Selection shown in the list
The signal list must highlight every selected signal.

*Parent: HLFR-00063*

### LLFR-00292 Only shown signals stay selected
A signal that is no longer shown in the signal list, because of the search (LLFR-00095), a deleted synthetic signal (LLFR-00255, LLFR-00597) or a closed data file (LLFR-00921, LLFR-00931), must no longer be selected.

*Parent: HLFR-00063, HLFR-00033*

### LLFR-00627 Hidden signals stay unselected
A signal that was deselected because it was no longer shown in the signal list (LLFR-00292) must stay unselected if it is shown again.

*Parent: HLFR-00063, HLFR-00033*

### LLFR-00293 Right-click with several signals selected
When the user right-clicks a signal, the app must select only that signal, deselecting any others, before it shows the signal menu (LLFR-00239).

*Parent: HLFR-00063, HLFR-00053*

### LLFR-00628 Menu acts on the right-clicked signal
When the user right-clicks a signal, the signal menu (LLFR-00239) must act on that signal, whatever other signals were selected before (LLFR-00293).

*Parent: HLFR-00063, HLFR-00053*

### LLFR-00294 Double-click with several signals selected
A double-click on a signal (LLFR-00019, LLFR-00020) must draw only the double-clicked signal, whatever other signals are selected.

*Parent: HLFR-00063, HLFR-00012*

### LLFR-00295 Enter key plots the selection
When the keyboard focus is in the signal list, at least one signal is selected and the user presses the Enter key, the app must create one new plot in the current tab, except as in LLFR-00630 and LLFR-00635.

Note: On a keyboard with both keys, Return and Enter act the same.

*Parent: HLFR-00064, HLFR-00018, HLFR-00058*

### LLFR-00629 Enter key draws every selected signal
When the app creates a plot with the Enter key (LLFR-00295), it must draw every selected signal in it, in the order of the signal list, using the curve colors of LLFR-00033 and LLFR-00034.

*Parent: HLFR-00064*

### LLFR-00630 Enter key in a full tab
If the tab is full when the user presses the Enter key as in LLFR-00295, the app must not create the plot, as in LLFR-00031 and LLFR-00032.

*Parent: HLFR-00064, HLFR-00018*

### LLFR-00631 Enter key with only FFT signals
When every selected signal is an FFT signal, the plot created with the Enter key (LLFR-00295) must be a frequency plot (LLFR-00256).

*Parent: HLFR-00064, HLFR-00058*

### LLFR-00296 Enter key with nothing to plot
The Enter key must not create a plot when no signal is selected, or when the keyboard focus is not in the signal list, for example while it is in the search box (LLFR-00094).

*Parent: HLFR-00064*

### LLFR-00632 No message for the Enter key with nothing to plot
The Enter key must not show any message when no signal is selected, or when the keyboard focus is not in the signal list, for example while it is in the search box (LLFR-00094).

*Parent: HLFR-00064*

### LLFR-00297 Drag several signals to a plot
When the user presses the left mouse button on a selected signal, drags and drops on a plot, the app must draw every selected signal in that plot, in the order of the signal list, using the curve colors of LLFR-00033 and LLFR-00034.

*Parent: HLFR-00065*

### LLFR-00633 Several signals dropped outside a plot
When the user drags the selected signals as in LLFR-00297, dropping them anywhere other than on a plot must behave as in LLFR-00022 and LLFR-00023.

*Parent: HLFR-00065*

### LLFR-00298 Drag a signal that is not selected
When the user presses the left mouse button on a signal that is not selected and drags it, the app must select only that signal.

*Parent: HLFR-00063, HLFR-00013*

### LLFR-00634 Unselected signal dragged alone
When the user presses the left mouse button on a signal that is not selected and drags it, the app must drag it alone (LLFR-00021).

*Parent: HLFR-00063, HLFR-00013*

### LLFR-00299 Selected signals already in the plot
When several signals are dropped on a plot (LLFR-00297), the app must apply LLFR-00056 and LLFR-00057 to each signal, so that it draws the others and shows no message about those already in the plot.

*Parent: HLFR-00065*

### LLFR-00300 FFT and time signals selected together
If the Enter key (LLFR-00295) is pressed while the selection holds both FFT signals and other signals, or a drop (LLFR-00297) holds any signal that cannot be drawn in the plot (LLFR-00257), the app must draw none of the selected signals.

*Parent: HLFR-00064, HLFR-00065, HLFR-00058*

### LLFR-00635 No plot for FFT and time signals together
In the cases of LLFR-00300, the app must not create a plot.

*Parent: HLFR-00064, HLFR-00065, HLFR-00058*

### LLFR-00636 Message for FFT and time signals together
In the cases of LLFR-00300, the app must show the information box of LLFR-00257.

*Parent: HLFR-00064, HLFR-00065, HLFR-00058*

### LLFR-00301 One undoable action for several signals
Plotting several signals with the Enter key (LLFR-00295, LLFR-00629) or a drop (LLFR-00297) must be one undoable action (LLFR-00140), so that one undo removes the new plot or all the curves that the drop added.

*Parent: HLFR-00064, HLFR-00065, HLFR-00040*

### LLFR-00302 Selection keys over the signal list
When the user presses the Data tip key or the Shift key while the mouse pointer is over the signal list panel, the app must not apply LLFR-00148 or LLFR-00154.

Note: These keys select signals in the list (LLFR-00625, LLFR-00626), so using them there does not change the plot tool.

*Parent: HLFR-00063, HLFR-00032*

### LLFR-00637 Selection key released over the signal list
When the user releases the Data tip key or the Shift key after pressing it as in LLFR-00302, the app must leave the active plot tool unchanged.

Note: These keys select signals in the list (LLFR-00625, LLFR-00626), so using them there does not change the plot tool.

*Parent: HLFR-00063, HLFR-00032*

### LLFR-00332 Green time signal name
The signal list panel must show the name of the time signal of each open data file (LLFR-00053, LLFR-00326, LLFR-00904) in a green that is easy to read against the list's background, including in search results (LLFR-00095) and while the signal is selected (LLFR-00291).

*Parent: HLFR-00071*

### LLFR-00638 Other signal names not green
The signal list panel must show the names of all the signals other than the time signals of the open data files in colors other than the green of LLFR-00332, including in search results (LLFR-00095) and while the signal is selected (LLFR-00291).

*Parent: HLFR-00071*

### LLFR-00362 File name row
The signal list must show, for each open data file, a file name row in bold letters with `file`, the file's number (LLFR-00895), `_` and the name of the data file with its extension and without its folder, for example `file1_run_A.csv`.

*Parent: HLFR-00079, HLFR-00033, HLFR-00063, HLFR-00114*

### LLFR-00933 Order of the files in the signal list
The signal list must show the open data files in the order of their numbers (LLFR-00895), each one starting with its file name row (LLFR-00362).

*Parent: HLFR-00079, HLFR-00011, HLFR-00113*

### LLFR-00934 Signals below their file name row
The signal list must show the signals of each data file directly below its file name row, in the file's order, followed by the synthetic signals of that file (LLFR-00242).

*Parent: HLFR-00079, HLFR-00011, HLFR-00113*

### LLFR-00639 File name row stays above its signals
Each file name row (LLFR-00362) must stay directly above the shown signals of its file (LLFR-00934), in the order of LLFR-00933, whatever the text in the search box.

*Parent: HLFR-00079, HLFR-00033*

### LLFR-00640 Search never hides the file name row
The search (LLFR-00095) must never hide a file name row (LLFR-00362).

*Parent: HLFR-00079, HLFR-00033*

### LLFR-00641 File name row when nothing matches
When no signal of an open data file matches the text in the search box, the file name row of that file (LLFR-00362) must stay in its place (LLFR-00933), with the text "No matching signals" below it (LLFR-00097).

*Parent: HLFR-00079, HLFR-00033*

### LLFR-00642 File name row is not a signal
A file name row (LLFR-00362) must not be a signal.

*Parent: HLFR-00079*

### LLFR-00643 File name row not selected
A file name row (LLFR-00362) must not be selected (LLFR-00290, LLFR-00625, LLFR-00626).

*Parent: HLFR-00079, HLFR-00063*

### LLFR-00644 File name row not in a Shift range
A click with the Shift key held (LLFR-00626) must never include a file name row (LLFR-00362) in the selection, even when the range covers signals of several data files.

*Parent: HLFR-00079, HLFR-00063*

### LLFR-00645 File name row not dragged
A file name row (LLFR-00362) must not be dragged.

*Parent: HLFR-00079*

### LLFR-00646 File name row not plotted
A file name row (LLFR-00362) must not be plotted, so that a double-click on it (LLFR-00019) and the Enter key (LLFR-00295, LLFR-00629) ignore it.

*Parent: HLFR-00079*

### LLFR-00647 File menu instead of the signal menu
A right-click on a file name row (LLFR-00362) must show the file menu (LLFR-00918) instead of the signal menu (LLFR-00239).

*Parent: HLFR-00079, HLFR-00118*

### LLFR-00648 Long file name shortened
When the text in a file name row (LLFR-00362) does not fit in the panel's width, the app must shorten it with "..." in the middle.

*Parent: HLFR-00079*

### LLFR-00649 Whole file name in a tip
When the text in a file name row (LLFR-00362) does not fit in the panel's width, the app must show the whole text in a tip while the mouse pointer is over the row.

*Parent: HLFR-00079*

### LLFR-00363 File name rows follow the open files
The signal list must show a file name row (LLFR-00362) only for each data file that is open.

*Parent: HLFR-00079, HLFR-00113*

### LLFR-00650 File name row on open
When the app opens a data file (LLFR-00915), it must add the file name row of that file (LLFR-00362) in the place of LLFR-00933.

*Parent: HLFR-00079, HLFR-00117*

### LLFR-00651 No file name row for a file that is not opened
When opening a selected file fails, is cancelled or is refused (LLFR-00007, LLFR-00010, LLFR-00327, LLFR-00891, LLFR-00893, LLFR-00949), the app must add no file name row (LLFR-00362) for that file.

*Parent: HLFR-00079, HLFR-00101*

### LLFR-00918 File menu
When the user right-clicks a file name row (LLFR-00362), the app must show a menu with the options "Close file" and "Close all files", in this order.

*Parent: HLFR-00118, HLFR-00119*

### LLFR-00919 Close file question
When the user chooses "Close file" (LLFR-00918), the app must ask the user whether to proceed, naming the file as its file name row shows it (LLFR-00362) and saying that:
- its signals and the synthetic signals computed from them will be removed from the signal list and from the plots;
- the tabs left with no plot will be closed;
- the flags and areas outside the time range of the files left will be deleted;
- the undo and redo history will be cleared.

Note: The question is asked even when no signal of the file is drawn.

*Parent: HLFR-00118*

### LLFR-00920 Close file declined
If the user does not proceed in the question of LLFR-00919, the app must keep the open data files, the signal list, the plots and the undo and redo history unchanged.

*Parent: HLFR-00118*

### LLFR-00921 Signals of a closed file removed
If the user proceeds in the question of LLFR-00919, the app must remove from the signal list the file name row of that file, its signals, and every synthetic signal computed from one of those signals, directly or through other synthetic signals, including a Product with signal that belongs to another file (LLFR-00935).

*Parent: HLFR-00118*

### LLFR-00922 Curves of a closed file removed
If the user proceeds in the question of LLFR-00919, the app must remove the curves of the signals of LLFR-00921 from every plot in every tab, with their pinned data tips and the delta markers that have a point on them (LLFR-00178).

*Parent: HLFR-00118, HLFR-00022*

### LLFR-00923 Plots left with no curve after a close
When closing a data file leaves a plot with no curve, the app must delete that plot as in LLFR-00051, with its text notes and arrows (LLFR-00744, LLFR-00777).

Note: A frequency plot whose FFT signals all belonged to the closed file is deleted in the same way.

*Parent: HLFR-00118, HLFR-00019*

### LLFR-00924 First point discarded on a close
When closing a data file removes the curve of a first point (LLFR-00163), the app must discard the first point and its dot.

*Parent: HLFR-00118, HLFR-00043, HLFR-00044*

### LLFR-00925 History cleared on a close
If the user proceeds in the question of LLFR-00919, the app must clear the undo and redo history.

Note: Closing a data file is not an undoable action (LLFR-00140).

*Parent: HLFR-00118, HLFR-00040, HLFR-00048*

### LLFR-00926 Other files kept on a close
When the app closes a data file, it must keep the other open data files unchanged, with their numbers (LLFR-00896), signals, synthetic signals and curves, except as in LLFR-00921 and LLFR-00922.

*Parent: HLFR-00118*

### LLFR-00927 Tabs emptied by a close are closed
When closing data files leaves with no plot a tab that held at least one plot before the close, the app must close that tab, except as in LLFR-00956.

*Parent: HLFR-00118, HLFR-00119, HLFR-00016*

### LLFR-00955 Empty tabs kept on a close
When the app closes data files, it must keep every tab that held no plot before the close.

*Parent: HLFR-00118, HLFR-00119, HLFR-00014*

### LLFR-00956 One tab kept on a close
When closing data files would close every tab (LLFR-00927), the app must keep the first of those tabs in tab order, with no plot, so that at least one tab always exists (LLFR-00066).

*Parent: HLFR-00118, HLFR-00119, HLFR-00014*

### LLFR-00957 Tab shown after a close
When a close (LLFR-00927) closes the tab that is shown, the app must show the nearest tab that is left to its left, or, when no tab is left to its left, the nearest tab that is left to its right.

*Parent: HLFR-00118, HLFR-00119, HLFR-00014*

### LLFR-00928 Flags outside the files left deleted on a close
When the app closes data files and at least one plot is left, it must delete every flag whose time is outside the time range of the open data files that are left (LLFR-00911), keeping a flag whose time is on an end of that range.

Note: The deletion is part of the close, which clears the undo and redo history (LLFR-00925). When no plot is left, every flag is deleted (LLFR-00667).

*Parent: HLFR-00118, HLFR-00119, HLFR-00031*

### LLFR-00945 Areas outside the files left deleted on a close
When the app closes data files and at least one plot is left, it must delete every area that lies entirely outside the time range of the open data files that are left (LLFR-00911), keeping an area that is partly inside that range or touches one of its ends.

Note: The deletion is part of the close, which clears the undo and redo history (LLFR-00925). When no plot is left, every area is deleted (LLFR-00711).

*Parent: HLFR-00118, HLFR-00119, HLFR-00069*

### LLFR-00961 Area partly outside the files left, resized
When the user starts to resize an area (LLFR-00313) that lies partly outside the time range of the open data files (LLFR-00911), the app must first limit the area to that time range.

Note: A move of such an area is limited by LLFR-00713.

*Parent: HLFR-00106, HLFR-00118, HLFR-00119*

### LLFR-00929 Close all files question
When the user chooses "Close all files" (LLFR-00918), the app must ask the user once whether to proceed, saying that:
- all the open data files will be closed;
- their signals and synthetic signals will be removed from the signal list and from the plots;
- the tabs left with no plot will be closed;
- every flag and every area will be deleted, because no file is left;
- the undo and redo history will be cleared.

*Parent: HLFR-00119*

### LLFR-00930 Close all files declined
If the user does not proceed in the question of LLFR-00929, the app must keep the open data files, the signal list, the plots and the undo and redo history unchanged.

*Parent: HLFR-00119*

### LLFR-00931 Close all files action
If the user proceeds in the question of LLFR-00929, the app must close every open data file as in LLFR-00921, LLFR-00922, LLFR-00923, LLFR-00924, LLFR-00925, LLFR-00927, LLFR-00955, LLFR-00956 and LLFR-00957, with no further question.

*Parent: HLFR-00119*

### LLFR-00932 Signal list after Close all files
After the app closes every data file (LLFR-00931), the signal list panel must show the same content as when the app starts with no data file open: no file name row and no signal.

*Parent: HLFR-00119, HLFR-00011*

### LLFR-00424 Search box bottom edge
The bottom edge of the search box (LLFR-00094) must be at the same height as the bottom edge of the lowest plot of the current tab, including its x-axis numbers and label, at any window size.

*Parent: HLFR-00095*

### LLFR-00652 Search box bottom edge with no plot
When the current tab holds no plot, the bottom edge of the search box (LLFR-00094) must be at the height where the bottom edge of a plot would be (LLFR-00424), at any window size.

*Parent: HLFR-00095*

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

### LLFR-00210 New tab name
The app must name each new tab "Tab N", where N grows by 1 for each new tab, skipping every number whose name another tab already has (LLFR-00212).

*Parent: HLFR-00015*

### LLFR-00653 Tab numbers not reused
When the app names a new tab (LLFR-00210), it must not reuse the number of a deleted tab, even when the tab's creation is undone.

*Parent: HLFR-00015*

### LLFR-00654 Tab numbering restart
The numbering of new tabs (LLFR-00210) must restart with "Tab 1" only when the app starts.

Note: Opening or closing data files never restarts the tab numbering, even when a close closes tabs (LLFR-00927).

*Parent: HLFR-00015*

### LLFR-00212 New tab name not in use
When the app names a new tab (LLFR-00210), it must skip every number N for which another tab is already named "Tab N", so that no two tabs share a name.

Note: For example, after the user renames "Tab 2" to "Tab 3", the next new tab is named "Tab 4". Names are compared as in LLFR-00658.

*Parent: HLFR-00015*

### LLFR-00655 Skipped tab numbers used up
A number skipped when the app names a new tab (LLFR-00212) must be used up like the number of a deleted tab (LLFR-00653).

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
The data tip must show the y-axis value as stored in its data file, without a unit.

*Parent: HLFR-00024*

### LLFR-00045 Pin a data tip
If the user left-clicks a curve while the hover data tip (LLFR-00042) is shown, the app must fix the data tip at that point in the plot, except as in LLFR-00886.

*Parent: HLFR-00025*

### LLFR-00046 Pinned data tip menu
When the user right-clicks a pinned data tip, the app must show a menu with the options "Delete", "Delete all data tips in this plot" and "Delete all data tips in all plots", in this order.

*Parent: HLFR-00025, HLFR-00093*

### LLFR-00047 Remove a pinned data tip
When the user chooses "Delete" in the pinned data tip menu (LLFR-00046), the app must remove the pinned data tip from the plot.

*Parent: HLFR-00025*

### LLFR-00048 Plot menu delete option
When the user right-clicks an empty area of a plot (not on a curve, a pinned data tip, a flag, a delta marker, an area, a text note or an arrow), the app must show a menu with a "Delete plot" option.

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
If the user enters a tab name that is empty or made only of spaces (LLFR-00030), the app must keep the tab's previous name.

*Parent: HLFR-00017*

### LLFR-00656 No message on an empty tab name
If the user enters a tab name that is empty or made only of spaces (LLFR-00030), the app must not show any message.

*Parent: HLFR-00017*

### LLFR-00211 Unique tab name on rename
If the user enters a tab name (LLFR-00030) that, without leading and trailing spaces, is the name of another tab, the app must keep the tab's previous name. Entering the tab's own current name is not a conflict.

Note: The app stores a tab name without its leading and trailing spaces. A rejected rename changes nothing, so it is not an undoable action (LLFR-00140).

*Parent: HLFR-00017*

### LLFR-00657 Tab name in use message
If the user enters a tab name (LLFR-00030) that, without leading and trailing spaces, is the name of another tab, the app must show an information box saying that a tab with that name already exists. Entering the tab's own current name is not a conflict.

Note: The information box is not an error box (HLFR-00002), like the Full Tab Notification box (LLFR-00032).

*Parent: HLFR-00017*

### LLFR-00658 Tab name comparison
When the app compares a tab name with the names of the other tabs (LLFR-00211, LLFR-00657), it must compare the names exactly, so that names that differ only in uppercase and lowercase letters are different names.

*Parent: HLFR-00017*

### LLFR-00068 Time on the x-axis
Every time plot (HLFR-00058) must have on its x-axis the time, in seconds, given by the time signals of the data files of its curves (HLFR-00006, LLFR-00907).

*Parent: HLFR-00012, HLFR-00013, HLFR-00007, HLFR-00116*

### LLFR-00069 Vertical stacking of plots
The plots in a tab must be stacked vertically, one below the other.

*Parent: HLFR-00014, HLFR-00018*

### LLFR-00070 Shared time axis
All time plots in all tabs must share the same x-axis range, so that a change to the time range of one time plot applies to every time plot in every tab.

*Parent: HLFR-00014, HLFR-00027, HLFR-00036*

### LLFR-00906 Curves of different files in one time plot
The app must let the user draw signals of different data files in the same time plot, by drop or the Enter key (LLFR-00021, LLFR-00295, LLFR-00297), in the same way as signals of one file.

*Parent: HLFR-00116, HLFR-00013, HLFR-00064, HLFR-00065*

### LLFR-00907 Each curve on the time of its own file
The app must draw each curve of a time plot with the samples of its signal placed at the times of the time signal of the signal's own data file.

*Parent: HLFR-00116, HLFR-00006, HLFR-00007*

### LLFR-00908 Same time origin for every file
The app must place the times of every data file on the shared x-axis (LLFR-00070) as they are stored in the file, with the same time origin for every file and no offset between files.

*Parent: HLFR-00116, HLFR-00007*

### LLFR-00909 Data tip time of its own file
The x-axis value of a data tip on a time plot (LLFR-00043) must be the time of the point in the time signal of the curve's own data file.

*Parent: HLFR-00116, HLFR-00024*

### LLFR-00910 Delta marker points on curves of different files
The app must let the two points of a delta marker (LLFR-00164) be on curves of different data files, each point taking its time from the time signal of its own curve's file (LLFR-00907).

*Parent: HLFR-00116, HLFR-00043, HLFR-00044*

### LLFR-00074 Mouse wheel zoom
When the user turns the mouse wheel forward over a plot, the app must zoom in the plot's x-axis, centered on the time (the frequency, on a frequency plot) under the mouse pointer.

*Parent: HLFR-00027*

### LLFR-00659 Mouse wheel zoom out
When the user turns the mouse wheel backward over a plot, the app must zoom out the plot's x-axis, centered on the time (the frequency, on a frequency plot) under the mouse pointer.

*Parent: HLFR-00027*

### LLFR-00075 Zoom on the x-axis only
The user must not be able to zoom the y-axis of a plot.

Note: The app still adjusts the y-axis range by itself, as described in LLFR-00076.

*Parent: HLFR-00027*

### LLFR-00076 Curves visible at any zoom
After every zoom, the app must set the y-axis range of each plot so that every curve in that plot is fully visible within the shown x-axis range.

*Parent: HLFR-00027*

### LLFR-00078 Click to zoom
While the Zoom button (LLFR-00077) is active and the user left-clicks a plot and releases the button less than 5 pixels from where it was pressed (LLFR-00208), the app must narrow the plot's x-axis range to 95% of its width, centered on the time (the frequency, on a frequency plot) of the clicked point, except as in LLFR-00886.

*Parent: HLFR-00027*

### LLFR-00081 Place a flag by click
While the Flag button (LLFR-00080) is active and the user left-clicks a plot anywhere other than on an existing flag, the app must draw a new flag at the time of the clicked point on every plot (LLFR-00205), except as in LLFR-00886.

*Parent: HLFR-00028*

### LLFR-00082 Flag height
A flag must cover the whole y-axis range shown in its plot, also after that range changes.

*Parent: HLFR-00028*

### LLFR-00083 Default flag color and reserved marker color
The app must give every new flag the reserved marker color, the orange `#ff8000`, which it never uses for curves (LLFR-00033, LLFR-00034). The user may give a flag (LLFR-00392) or a delta marker (LLFR-00409) any color, including a color of the curve palette.

Note: A flag stays easy to tell from a curve by its dashed line (LLFR-00143) and its name label (LLFR-00084).

*Parent: HLFR-00028, HLFR-00020*

### LLFR-00660 Other uses of the reserved marker color
The reserved marker color (LLFR-00083) must also be the color of every new delta marker (LLFR-00172), of every new arrow (LLFR-00770), of the border of every new text note (LLFR-00740), of the dot of a first point (LLFR-00680), of the delta marker previews (LLFR-00352, LLFR-00353), of the time span selection (LLFR-00208) and of the flag preview (LLFR-00203), whatever color the user gave to the flags or to the delta markers.

*Parent: HLFR-00028, HLFR-00020*

### LLFR-00084 Flag label
The app must show the name of a flag in a label at the top of its line.

*Parent: HLFR-00028*

### LLFR-00085 Default flag name
The app must name each new flag "Flag N", where N is 1 for the first flag placed after the app starts and grows by 1 for each new flag.

Note: Flags are shared by all plots (LLFR-00205), so the numbering is shared too. Opening or closing data files never restarts it.

*Parent: HLFR-00028*

### LLFR-00086 Drag a flag
While the Flag button (LLFR-00080) is active or no plot tool is active (LLFR-00382), and the user presses the left mouse button on a flag and drags it, the app must move the flag along the x-axis with the mouse pointer and leave it at the time where the button is released.

*Parent: HLFR-00029*

### LLFR-00087 Flag menu rename option
When the user right-clicks a flag, the app must show a menu with a "Rename" option.

*Parent: HLFR-00030*

### LLFR-00088 Rename flag action
When the user chooses "Rename" in the flag menu (LLFR-00087), the app must let the user type a new name for that flag.

*Parent: HLFR-00030*

### LLFR-00089 Empty flag name
If the user enters a flag name that is empty or made only of spaces (LLFR-00088), the app must keep the flag's previous name.

*Parent: HLFR-00030*

### LLFR-00661 No message on an empty flag name
If the user enters a flag name that is empty or made only of spaces (LLFR-00088), the app must not show any message.

*Parent: HLFR-00030*

### LLFR-00090 Flag menu delete option
When the user right-clicks a flag, the app must show a menu with a "Delete" option, directly followed by a "Delete all flags" option.

*Parent: HLFR-00031, HLFR-00093*

### LLFR-00091 Delete flag action
When the user chooses "Delete" in the flag menu (LLFR-00090), the app must remove that flag and its label from every plot.

*Parent: HLFR-00031*

### LLFR-00092 Flag time value
The app must show the time of a flag, in seconds, directly below the flag's label (LLFR-00084).

*Parent: HLFR-00028, HLFR-00007*

### LLFR-00093 Flag time value while dragging
While the user drags a flag (LLFR-00086), the app must update the flag's time value (LLFR-00092) to the flag's current position.

*Parent: HLFR-00029*

### LLFR-00203 Flag preview
While the Flag button (LLFR-00080) is active, including while the Shift key is held (LLFR-00154), and the mouse pointer is over a plot's drawing area but not over an existing flag, the app must show a preview of the flag that a click would place on every time plot of the current tab: a dashed vertical line at the time under the pointer, in a paler version of the reserved marker color (LLFR-00083), the color of a new flag, with its time value (LLFR-00092).

Note: Plots in tabs that are not shown don't need the preview.

*Parent: HLFR-00028*

### LLFR-00662 Flag preview hidden
The app must hide the flag preview (LLFR-00203) when the pointer leaves the plot's drawing area, moves over an existing flag, or the Flag button is deactivated.

*Parent: HLFR-00028*

### LLFR-00663 Flag preview not exported
The flag preview (LLFR-00203) must not appear in the PDF export (LLFR-00129) or the copied image (LLFR-00133).

*Parent: HLFR-00028*

### LLFR-00205 Flags on every plot
Every flag must be shown on every time plot in every tab, including time plots created after the flag.

*Parent: HLFR-00028, HLFR-00029, HLFR-00030, HLFR-00031, HLFR-00089*

### LLFR-00664 Flag changes on every plot
Moving (LLFR-00086), renaming (LLFR-00088), changing the color of (LLFR-00392) or deleting (LLFR-00091) a flag on any time plot must apply to it on every time plot (LLFR-00205).

Note: Each of these remains one undoable action (LLFR-00140).

*Parent: HLFR-00028, HLFR-00029, HLFR-00030, HLFR-00031, HLFR-00089*

### LLFR-00665 Dragged flag in the current tab
While a flag is dragged (LLFR-00086), it must follow the pointer on every time plot of the current tab.

*Parent: HLFR-00029*

### LLFR-00666 Dragged flag in the other tabs
While a flag is dragged (LLFR-00086), on the time plots of the other tabs it must be at its new time at the latest when the button is released.

*Parent: HLFR-00029*

### LLFR-00667 Flags deleted with the last plot
When no plot is left in any tab, whether because a plot is deleted (LLFR-00049, LLFR-00051), a tab is deleted (LLFR-00028) or data files are closed (LLFR-00921 to LLFR-00923, LLFR-00931), the app must delete every flag.

*Parent: HLFR-00028, HLFR-00031, HLFR-00118, HLFR-00119*

### LLFR-00668 Flags deleted in the same action
When the flags are deleted because no plot is left (LLFR-00667) and the cause is deleting a plot or a tab, the flags must be deleted as part of that same action, so that undoing it (LLFR-00138) brings the flags back.

Note: This remains one undoable action (LLFR-00140).

*Parent: HLFR-00028, HLFR-00031*

### LLFR-00106 Tab alignment
The tabs must be aligned to the left of the top edge of the plot panel, with the first tab starting at the panel's left edge.

*Parent: HLFR-00014*

### LLFR-00107 Add tab button style
The "+" button (LLFR-00025) must have the same height, background, border and corner shape as an unselected tab, like the new tab button of a modern web browser.

*Parent: HLFR-00015*

### LLFR-00669 Add tab button width
The "+" button (LLFR-00025) must be narrower than a tab, like the new tab button of a modern web browser.

*Parent: HLFR-00015*

### LLFR-00108 Wheel zoom with any plot tool
The app must apply mouse wheel zoom (LLFR-00074, LLFR-00659) whether or not a plot tool is active.

Note: Mouse wheel zoom is not a plot tool (HLFR-00032).

*Parent: HLFR-00027, HLFR-00032*

### LLFR-00110 Flag menu over a curve
When the user right-clicks a point where a flag overlaps a curve, the app must show the flag menu (LLFR-00087, LLFR-00090) and not the curve menu (LLFR-00038, LLFR-00040).

*Parent: HLFR-00030, HLFR-00031*

### LLFR-00111 Flag numbers not reused
The app must not reuse the number of a deleted flag (LLFR-00085) for a new flag, even when the flag's placement is undone, while the app runs.

*Parent: HLFR-00028*

### LLFR-00112 Renamed flag label
After the user types a new flag name (LLFR-00088), the app must show the new name in the flag's label (LLFR-00084).

*Parent: HLFR-00030*

### LLFR-00113 Wheel zoom step
Each notch of the mouse wheel (15 degrees of rotation) turned forward must change the x-axis range of the plot by 5%, narrowing the range to 95% of its width.

*Parent: HLFR-00027*

### LLFR-00670 Wheel zoom step backward
Each notch of the mouse wheel (15 degrees of rotation) turned backward must change the x-axis range of the plot by 5%, widening the range to 1/0.95 of its width.

*Parent: HLFR-00027*

### LLFR-00671 Wheel zoom for smaller movements
Wheel movements smaller than a notch (LLFR-00113, LLFR-00670), such as from a touchpad, must zoom in proportion.

*Parent: HLFR-00027*

### LLFR-00206 Wheel direction on a trackpad
On macOS, the app must zoom in when the user's fingers move up on the trackpad, as with the mouse wheel turning forward (LLFR-00074), whatever the system's "natural scrolling" setting.

*Parent: HLFR-00027*

### LLFR-00672 Trackpad fingers down zoom out
On macOS, the app must zoom out when the user's fingers move down on the trackpad, as with the mouse wheel turning backward (LLFR-00659), whatever the system's "natural scrolling" setting.

*Parent: HLFR-00027*

### LLFR-00208 Time span selection
While the Zoom button (LLFR-00077) is active and the user presses the left mouse button on a plot and moves the pointer 5 pixels or more from where the button was pressed, the app must show a horizontal dashed line at the height of the press, from the time of the press to the time under the pointer (the frequencies, on a frequency plot), with a short vertical line at each end, in the reserved marker color (LLFR-00083, LLFR-00172).

*Parent: HLFR-00027*

### LLFR-00209 Zoom to the selected span
When the user releases the left mouse button after LLFR-00208, the app must set the plot's x-axis range to the selected time span, so that its two ends are the plot's left and right edges, applied to every time plot (LLFR-00070). On a frequency plot, the span zoom changes only that plot (LLFR-00693).

Note: A release less than 5 pixels from the press is a click (LLFR-00078).

*Parent: HLFR-00027*

### LLFR-00673 Y-axis ranges after a span zoom
When the span zoom (LLFR-00209) sets the x-axis range, the app must set the y-axis ranges as in LLFR-00076.

*Parent: HLFR-00027*

### LLFR-00674 Selection line removed
When the user releases the left mouse button after LLFR-00208, the app must remove the selection line.

*Parent: HLFR-00027*

### LLFR-00675 Span end outside the drawing area
If the left mouse button is released outside the plot's drawing area after LLFR-00208, the end of the selected span (LLFR-00209) must be the time at the nearer left or right edge of the drawing area.

*Parent: HLFR-00027*

### LLFR-00676 Span limited to the files
The span of the span zoom (LLFR-00209) must be limited to the time range of the open data files (LLFR-00911, LLFR-00119). On a frequency plot, the span zoom is limited as in LLFR-00694.

*Parent: HLFR-00027*

### LLFR-00911 Time range of the open data files
The app must take as the time range of the open data files the range from the earliest first time sample to the latest last time sample of all the open data files.

Note: Reset zoom (LLFR-00115), the first time plot (LLFR-00688), the pan limits (LLFR-00119), the span zoom (LLFR-00676), the area limits (LLFR-00713, LLFR-00715) and the layout checks (LLFR-00233, LLFR-00234, LLFR-00487, LLFR-00319) use this range.

*Parent: HLFR-00035, HLFR-00036, HLFR-00113*

### LLFR-00912 X-axis range kept when a file is opened
When the app opens a data file while at least one time plot exists, it must keep the x-axis range shared by the time plots (LLFR-00070) unchanged.

Note: The user can then press Reset zoom to see the time range of all the open data files.

*Parent: HLFR-00113, HLFR-00117, HLFR-00035*

### LLFR-00913 X-axis range limited when a file is closed
When the app closes data files and time plots are left whose shared x-axis range (LLFR-00070) goes beyond the time range of the open data files that are left (LLFR-00911), the app must limit the x-axis range to that time range, except as in LLFR-00914.

*Parent: HLFR-00118, HLFR-00119, HLFR-00036*

### LLFR-00914 X-axis range outside the files left
When the app closes data files and the shared x-axis range of the time plots that are left does not overlap the time range of the open data files that are left (LLFR-00911), the app must show the whole time range of those files.

*Parent: HLFR-00118, HLFR-00119, HLFR-00035*

### LLFR-00115 Reset zoom action
When the user clicks the Reset zoom button (LLFR-00114), the app must set the x-axis range of every time plot in every tab to the time range of the open data files (LLFR-00911). Frequency plots are reset as in LLFR-00695.

*Parent: HLFR-00035*

### LLFR-00677 Y-axis ranges after a zoom reset
When the user clicks the Reset zoom button (LLFR-00114), the app must set the y-axis ranges of every time plot in every tab as in LLFR-00076.

*Parent: HLFR-00035*

### LLFR-00117 Pan by wheel drag
When the user holds the mouse wheel pressed over a plot and moves the mouse left or right, the app must shift the plot's x-axis range so that the curves follow the mouse pointer horizontally, whether or not a plot tool is active.

*Parent: HLFR-00036*

### LLFR-00118 No pan without zoom
While a plot shows the whole time range of the open data files (LLFR-00911) (for a frequency plot, its whole frequency range, LLFR-00692), holding the mouse wheel pressed and moving the mouse, or a horizontal two-finger swipe (LLFR-00345), must not change the plot's x-axis range.

*Parent: HLFR-00036*

### LLFR-00119 Pan limits
The app must not pan a time plot's x-axis range before the earliest first time sample or after the latest last time sample of the open data files (LLFR-00911). A frequency plot's pan is limited as in LLFR-00694.

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

### LLFR-00143 Dashed flag line
The app must draw the line of a flag as a dashed line.

*Parent: HLFR-00028*

### LLFR-00144 First three curve colors
The first three colors of the palette of LLFR-00033 must be blue, black and a dark red that stays clearly different from the marker color (LLFR-00365), in that order, so that the first curve drawn in a plot is blue, the second black and the third red.

*Parent: HLFR-00020*

### LLFR-00147 Grid shown at start
Every time the app starts, the grid must be shown, whatever the user chose the last time the app was open.

Note: The user can still hide the grid (LLFR-00123). Loading a layout applies the layout file's grid setting (LLFR-00481).

*Parent: HLFR-00037*

### LLFR-00678 Grid button active at start
Every time the app starts, the Grid button must show its active color (LLFR-00124), whatever the user chose the last time the app was open.

*Parent: HLFR-00037*

### LLFR-00151 Data tip leader line
The app must connect each pinned data tip (LLFR-00045) to the point whose values it shows with a dashed line.

*Parent: HLFR-00025*

### LLFR-00152 Drag a pinned data tip
When the user presses the left mouse button on a pinned data tip and drags it, the app must move the data tip with the mouse pointer and leave it where the button is released, while the data tip keeps showing the values of the same point.

*Parent: HLFR-00041*

### LLFR-00153 Press on a pinned data tip
A left mouse button press on a pinned data tip must start moving it (LLFR-00152), whether or not a plot tool is active, except as in LLFR-00383.

*Parent: HLFR-00041, HLFR-00032*

### LLFR-00679 Press on a pinned data tip does nothing else
A left mouse button press on a pinned data tip (LLFR-00153) must not pin a new data tip, zoom, pan, place or move a flag, create, move or resize an area, start or move a text note, draw, move, rotate or stretch an arrow, or pick a delta marker point.

*Parent: HLFR-00041, HLFR-00032*

### LLFR-00163 Pick the first point
While the Delta X button (LLFR-00161) or the Delta Y button (LLFR-00162) is active and the user left-clicks a curve, the app must take the curve sample nearest to the mouse pointer as the first point of a measurement, except as in LLFR-00886.

*Parent: HLFR-00043, HLFR-00044*

### LLFR-00680 Dot of the first point
When the app takes a first point (LLFR-00163), it must mark it in the plot with a dot.

*Parent: HLFR-00043, HLFR-00044*

### LLFR-00164 Pick the second point
When the user then left-clicks a curve in the same plot, the app must take the curve sample nearest to the mouse pointer as the second point, except as in LLFR-00886. The two points may be on the same curve or on different curves.

*Parent: HLFR-00043, HLFR-00044*

### LLFR-00681 First point dot removed
When the app takes the second point (LLFR-00164), it must remove the dot of LLFR-00680, except as in LLFR-00431 and LLFR-00860.

*Parent: HLFR-00043, HLFR-00044*

### LLFR-00682 Draw the delta marker
When the app takes the second point (LLFR-00164), it must draw a Delta X marker (LLFR-00168) or a Delta Y marker (LLFR-00170, LLFR-00685) between the two points, according to the active button, except as in LLFR-00431.

*Parent: HLFR-00043, HLFR-00044*

### LLFR-00165 Click outside a curve
While a first point is picked (LLFR-00163), a left-click that is not on a curve must keep the first point.

*Parent: HLFR-00043, HLFR-00044*

### LLFR-00683 No message on a click outside a curve
While a first point is picked (LLFR-00163), a left-click that is not on a curve must not show any message.

*Parent: HLFR-00043, HLFR-00044*

### LLFR-00166 First point in another plot
While a first point is picked (LLFR-00163), a left-click on a curve in another plot must take the clicked sample as the new first point (LLFR-00163), except as in LLFR-00886.

*Parent: HLFR-00043, HLFR-00044*

### LLFR-00684 Old first point discarded
While a first point is picked (LLFR-00163), a left-click on a curve in another plot must discard the first point and its dot, except as in LLFR-00886.

*Parent: HLFR-00043, HLFR-00044*

### LLFR-00167 First point discarded
When the Delta X or Delta Y button is deactivated while a first point is picked (LLFR-00163), the app must discard the first point and remove its dot.

*Parent: HLFR-00043, HLFR-00044*

### LLFR-00168 Delta X marker
A Delta X marker must mark its two points with dots and draw a dashed horizontal curly bracket whose two ends are at the times of the two points, placed just above the higher of the two points, with its middle point pointing up, away from the points.

Note: The curly bracket gives delta markers a visual identity of their own, different from the straight dashed line of a flag (LLFR-00143), although a new flag and a new delta marker have the same color (LLFR-00083, LLFR-00172).

*Parent: HLFR-00043*

### LLFR-00169 Delta X value
A Delta X marker must show the text "Δt = <value> s" next to the middle point of its curly bracket, where the value is the time of the second point minus the time of the first point, in seconds, in the same number format as the data tip's x value (LLFR-00043).

*Parent: HLFR-00043, HLFR-00007*

### LLFR-00170 Delta Y marker
A Delta Y marker must mark its two points with dots and draw a dashed vertical curly bracket whose two ends are at the y-axis values of the two points, placed just to the right of the later of the two points, with its middle point pointing right, away from the points, except as in LLFR-00685.

*Parent: HLFR-00044*

### LLFR-00685 Mirrored Delta Y marker
When the bracket of a Delta Y marker (LLFR-00170), its value (LLFR-00171) and its label (LLFR-00427) do not fit to the right of the later point inside the plot's drawing area, the app must draw them mirrored, just to the left of the earlier of the two points, with the middle point pointing left.

Note: If neither side has room for the bracket, its value and its label, the app uses the side with more room. The bracket is cut at the edge of the plot only when one of its points is itself outside the shown x-axis range, or when the two points leave less room than the bracket needs on both sides.

*Parent: HLFR-00044*

### LLFR-00171 Delta Y value
A Delta Y marker must show the text "Δy = <value>" next to the middle point of its curly bracket, where the value is the y-axis value of the second point minus the y-axis value of the first point, without a unit, in the same number format as the data tip's y value (LLFR-00044).

*Parent: HLFR-00044*

### LLFR-00172 Delta marker color
The app must draw every new delta marker in the reserved marker color (LLFR-00083), which it never uses for curves (LLFR-00033, LLFR-00034), until the user chooses another color for it (LLFR-00409).

*Parent: HLFR-00043, HLFR-00044, HLFR-00020, HLFR-00092*

### LLFR-00686 First point dot and previews color
The dot of a first point (LLFR-00680) and the previews of LLFR-00352 and LLFR-00353 must always be drawn in the reserved marker color (LLFR-00083), whatever color the user gave to the flags or to the delta markers.

*Parent: HLFR-00043, HLFR-00044, HLFR-00020, HLFR-00092*

### LLFR-00173 Delta marker follows its points
A delta marker must stay attached to its two points when the plot's x-axis or y-axis range or the plot's size changes.

*Parent: HLFR-00043, HLFR-00044*

### LLFR-00687 Delta marker value unchanged
The value of a delta marker must stay unchanged when the plot's x-axis or y-axis range or the plot's size changes.

*Parent: HLFR-00043, HLFR-00044*

### LLFR-00174 Several delta markers
A plot must be able to hold any number of Delta X and Delta Y markers at the same time.

*Parent: HLFR-00043, HLFR-00044*

### LLFR-00175 Delta marker menu
When the user right-clicks a delta marker, the app must show a menu with the options "Rename", "Color", "Delete", "Delete all delta markers in this plot" and "Delete all delta markers in all plots", in this order.

*Parent: HLFR-00043, HLFR-00044, HLFR-00092, HLFR-00093, HLFR-00110*

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
When other time plots exist, a new time plot must show the x-axis range shared by the existing time plots (LLFR-00070).

*Parent: HLFR-00012, HLFR-00014*

### LLFR-00688 Time range of the first time plot
When no other time plot exists, a new time plot must show the time range of the open data files (LLFR-00911).

*Parent: HLFR-00012, HLFR-00014*

### LLFR-00256 Frequency plot
When the user double-clicks an FFT signal (LLFR-00019), the app must create a frequency plot in the current tab, with frequency in Hz on its x-axis, labeled "Frequency (Hz)".

*Parent: HLFR-00058*

### LLFR-00689 FFT signal drawn in its frequency plot
When the app creates a frequency plot by double-click (LLFR-00256), it must draw the double-clicked FFT signal in it.

*Parent: HLFR-00058*

### LLFR-00690 Frequency plots in the plot count
A frequency plot must count towards the maximum number of plots of a tab (HLFR-00018).

*Parent: HLFR-00058*

### LLFR-00257 FFT and time signals in separate plots
If the user drops an FFT signal on a time plot, or any other signal on a frequency plot, the app must not draw the signal.

*Parent: HLFR-00058, HLFR-00013*

### LLFR-00691 Message for FFT and time signals in one plot
If the user drops an FFT signal on a time plot, or any other signal on a frequency plot, the app must show an information box saying that FFT signals and time signals cannot be drawn in the same plot.

*Parent: HLFR-00058, HLFR-00013*

### LLFR-00258 Frequency plot x-axis range
Each frequency plot must have its own x-axis range, which follows neither the time plots (LLFR-00070) nor the other frequency plots.

*Parent: HLFR-00058, HLFR-00027, HLFR-00035, HLFR-00036*

### LLFR-00692 Frequency range of a new frequency plot
A new frequency plot must show the frequencies from 0 Hz up to the highest frequency of its curves.

*Parent: HLFR-00058*

### LLFR-00693 Zoom and pan on one frequency plot
On a frequency plot, mouse wheel zoom (LLFR-00074, LLFR-00659), click zoom (LLFR-00078), span zoom (LLFR-00209) and pan (LLFR-00117, LLFR-00345, LLFR-00356) must change only that frequency plot.

*Parent: HLFR-00058, HLFR-00027, HLFR-00036*

### LLFR-00694 Zoom and pan limits on a frequency plot
On a frequency plot, mouse wheel zoom (LLFR-00074, LLFR-00659), click zoom (LLFR-00078), span zoom (LLFR-00209) and pan (LLFR-00117, LLFR-00345, LLFR-00356) must be limited to the frequency range of LLFR-00692.

*Parent: HLFR-00058, HLFR-00027, HLFR-00036*

### LLFR-00695 Reset zoom on a frequency plot
Reset zoom (LLFR-00115) must return every frequency plot to the frequency range of LLFR-00692.

*Parent: HLFR-00058, HLFR-00035*

### LLFR-00259 No flags on frequency plots
The app must not show flags or their preview (LLFR-00203, LLFR-00205) on frequency plots.

*Parent: HLFR-00058, HLFR-00028*

### LLFR-00696 No flag placed on a frequency plot
A click on a frequency plot while the Flag button is active must not place a flag.

*Parent: HLFR-00058, HLFR-00028*

### LLFR-00260 Data tip on a frequency plot
A data tip on a frequency plot must show the x-axis value in Hz, instead of seconds (LLFR-00043).

*Parent: HLFR-00058, HLFR-00024*

### LLFR-00261 Delta X on a frequency plot
A Delta X marker on a frequency plot must show the text "Δf = <value> Hz", where the value is the frequency of the second point minus the frequency of the first point, instead of the text of LLFR-00169.

*Parent: HLFR-00058, HLFR-00043*

### LLFR-00303 Area preview while dragging
While the Area button (LLFR-00286) is active and the user presses the left mouse button on a time plot's drawing area, outside any area and more than 5 pixels from its edges, and moves the pointer 5 pixels or more from where the button was pressed, the app must show on that plot a preview of the area, from the time of the press to the time under the pointer, except as in LLFR-00697.

*Parent: HLFR-00066*

### LLFR-00697 Area preview stops at an area
The area preview (LLFR-00303) must stop at the edge of the nearest existing area, so that it never overlaps one.

*Parent: HLFR-00066*

### LLFR-00304 Create an area
When the user releases the left mouse button after LLFR-00303, the app must create an area between the two times, on every time plot (LLFR-00310), except as in LLFR-00700 and LLFR-00702.

*Parent: HLFR-00066*

### LLFR-00698 Area preview removed
When the user releases the left mouse button after LLFR-00303, the app must remove the preview.

*Parent: HLFR-00066*

### LLFR-00699 Area end outside the drawing area
If the left mouse button is released outside the plot's drawing area after LLFR-00303, the end of the area (LLFR-00304) must be the time at the nearer left or right edge of the drawing area.

*Parent: HLFR-00066*

### LLFR-00700 Short drag creates no area
After a press as in LLFR-00303, a release less than 5 pixels from the press must not create an area.

*Parent: HLFR-00066*

### LLFR-00701 No message on a short drag
After a press as in LLFR-00303, a release less than 5 pixels from the press must not show any message.

*Parent: HLFR-00066*

### LLFR-00702 Areas do not overlap
An area must not overlap another area, but two areas may share an edge.

*Parent: HLFR-00066*

### LLFR-00305 Area appearance
The app must draw an area as a see-through band in the area's color (LLFR-00351), shown paler than an opaque item of the same color because it is see-through, between its start and end times, covering the whole y-axis range shown in the plot.

*Parent: HLFR-00066*

### LLFR-00703 Area height follows the y-axis range
When the y-axis range shown in a plot changes, the app must keep each area (LLFR-00305) covering that whole range.

*Parent: HLFR-00066*

### LLFR-00306 Area behind the other items
The app must draw an area behind the curves, grid, flags, delta markers, data tips, text notes and arrows, so that they stay visible.

*Parent: HLFR-00066*

### LLFR-00307 Area label
The app must show the name of an area in a label in the upper-left corner of the band, inside the plot's drawing area.

Note: When the start of the area is left of the shown time range, the label is in the upper-left corner of the part of the band that is shown.

*Parent: HLFR-00066*

### LLFR-00704 Area label color
The text of the label of an area (LLFR-00307) must be drawn in the area's color (LLFR-00351) at full opacity, on the label's box that keeps it readable, while the band stays see-through (LLFR-00305).

*Parent: HLFR-00066*

### LLFR-00308 Area time values
The app must show the start and end times of an area, in seconds, directly below its label (LLFR-00307), in the area's color at full opacity on a label box as in LLFR-00704.

*Parent: HLFR-00066, HLFR-00067, HLFR-00007, HLFR-00106*

### LLFR-00705 Area time values while dragging
While the user moves or resizes an area (LLFR-00312, LLFR-00313), the app must update its start and end times (LLFR-00308) to the area's current position.

*Parent: HLFR-00067, HLFR-00106*

### LLFR-00309 Default area name
The app must name each new area "Area N", where N is 1 for the first area created after the app starts and grows by 1 for each new area, except as in LLFR-00707.

*Parent: HLFR-00066*

### LLFR-00706 Area numbers not reused
The app must not reuse the number of a deleted area (LLFR-00309), even when the area's creation is undone, while the app runs.

*Parent: HLFR-00066*

### LLFR-00707 Renamed area number used up
When the user renames an area "Area N" (LLFR-00315), the number N must be used up, like a skipped tab number (LLFR-00655), so that a later new area never gets that name.

*Parent: HLFR-00066*

### LLFR-00310 Areas on every time plot
Every area must be shown on every time plot in every tab, including time plots created after the area.

*Parent: HLFR-00066, HLFR-00067, HLFR-00068, HLFR-00069, HLFR-00106*

### LLFR-00708 Area changes on every plot
Moving, resizing (LLFR-00312, LLFR-00313), renaming (LLFR-00315), changing the color of (LLFR-00351) or deleting (LLFR-00316) an area on any time plot must apply to it on every time plot (LLFR-00310).

Note: Each of these remains one undoable action (LLFR-00140).

*Parent: HLFR-00066, HLFR-00067, HLFR-00068, HLFR-00069, HLFR-00106*

### LLFR-00709 Dragged area in the current tab
While an area is dragged (LLFR-00312, LLFR-00313), it must follow the pointer on every time plot of the current tab.

*Parent: HLFR-00067, HLFR-00106*

### LLFR-00710 Dragged area in the other tabs
While an area is dragged (LLFR-00312, LLFR-00313), on the time plots of the other tabs it must be at its new position at the latest when the button is released.

*Parent: HLFR-00067, HLFR-00106*

### LLFR-00711 Areas deleted with the last plot
When no plot is left in any tab, the app must delete every area in the same way as flags (LLFR-00667, LLFR-00668), so that undoing the deletion of a plot or a tab brings the areas back.

Note: This remains one undoable action (LLFR-00140).

*Parent: HLFR-00066, HLFR-00069*

### LLFR-00311 No areas on frequency plots
The app must not show areas or their preview on frequency plots (HLFR-00058).

*Parent: HLFR-00066, HLFR-00058*

### LLFR-00712 No area created on a frequency plot
A drag on a frequency plot (HLFR-00058) while the Area button is active must not create an area.

*Parent: HLFR-00066, HLFR-00058*

### LLFR-00312 Move an area
While the Area button (LLFR-00286) is active or no plot tool is active (LLFR-00790), and the user presses the left mouse button inside an area, more than 5 pixels from both of its edges, and drags, the app must move the area along the x-axis with the mouse pointer, keeping its width, and leave it where the button is released, except as in LLFR-00713 and LLFR-00714.

*Parent: HLFR-00067*

### LLFR-00713 Moved area within the files
While the user moves an area (LLFR-00312), the whole area must stay within the time range of the open data files (LLFR-00911).

*Parent: HLFR-00067*

### LLFR-00714 Moved area stops at the next area
While the user moves an area (LLFR-00312), the area must stop at the edge of the next area, so that it never overlaps one.

*Parent: HLFR-00067*

### LLFR-00313 Resize an area
While the Area button (LLFR-00286) is active or no plot tool is active (LLFR-00790), and the user presses the left mouse button within 5 pixels of an edge of an area and drags, the app must move that edge along the x-axis with the mouse pointer, and leave it where the button is released, while the other edge stays in place, except as in LLFR-00715, LLFR-00716 and LLFR-00717.

*Parent: HLFR-00106*

### LLFR-00715 Resized edge within the files
While the user resizes an area (LLFR-00313), the moved edge must stay within the time range of the open data files (LLFR-00911).

*Parent: HLFR-00106*

### LLFR-00716 Minimum area width
While the user resizes an area (LLFR-00313), the moved edge must stay at least 5 pixels from the other edge.

*Parent: HLFR-00106*

### LLFR-00717 Resized edge stops at the next area
While the user resizes an area (LLFR-00313), the moved edge must stop at the edge of the next area, so that the area never overlaps one.

*Parent: HLFR-00106*

### LLFR-00314 Area menu
When the user right-clicks an area, the app must show a menu with the options "Rename", "Color", "Delete", "Delete all areas" and "Delete plot", in this order.

Note: "Delete plot" acts as in LLFR-00049, so a plot whose whole shown range is covered by an area can still be deleted.

*Parent: HLFR-00068, HLFR-00069, HLFR-00019, HLFR-00093*

### LLFR-00315 Rename an area action
When the user chooses "Rename" in the area menu (LLFR-00314), the app must let the user type a new name for that area.

*Parent: HLFR-00068*

### LLFR-00718 Renamed area label
After the user types a new area name (LLFR-00315), the app must show it in the area's label (LLFR-00307), except as in LLFR-00719.

*Parent: HLFR-00068*

### LLFR-00719 Empty area name
If the user enters an area name (LLFR-00315) that is empty or made only of spaces, the app must keep the area's previous name.

*Parent: HLFR-00068*

### LLFR-00720 No message on an empty area name
If the user enters an area name (LLFR-00315) that is empty or made only of spaces, the app must not show any message.

*Parent: HLFR-00068*

### LLFR-00316 Delete an area action
When the user chooses "Delete" in the area menu (LLFR-00314), the app must remove that area and its label from every plot.

*Parent: HLFR-00069*

### LLFR-00317 Menus over an area
When the user right-clicks a point inside an area where a curve, a pinned data tip, a flag, a delta marker, a text note or an arrow is drawn, the app must show the menu of that item and not the area menu (LLFR-00314).

*Parent: HLFR-00068, HLFR-00069*

### LLFR-00721 Area menu only on the area alone
The app must show the area menu (LLFR-00314) only when the right-clicked point holds nothing but the area.

*Parent: HLFR-00068, HLFR-00069*

### LLFR-00318 Other plot tools over an area
While the Data tip, Zoom, Pan, Flag, Delta X, Delta Y, Text or Arrow button is active, a press inside an area must act as it does outside one, so that an area does not change what the other plot tools do with a press inside it.

*Parent: HLFR-00066, HLFR-00032, HLFR-00085*

### LLFR-00722 No area edit with the other plot tools
While the Data tip, Zoom, Pan, Flag, Delta X, Delta Y, Text or Arrow button is active, a press inside an area must not move or resize the area (LLFR-00799).

*Parent: HLFR-00066, HLFR-00032, HLFR-00085*

### LLFR-00723 Move an area with no plot tool
While no plot tool is active, a press inside an area more than 5 pixels from both of its edges must move it (LLFR-00312), unless another object that reacts to the press is drawn at that point (LLFR-00383).

*Parent: HLFR-00066, HLFR-00032, HLFR-00085*

### LLFR-00724 Resize an area with no plot tool
While no plot tool is active, a press within 5 pixels of an edge of an area must resize it (LLFR-00313), unless another object that reacts to the press is drawn at that point (LLFR-00383).

*Parent: HLFR-00066, HLFR-00032, HLFR-00085*

### LLFR-00319 Areas in a layout
When loading a layout, the app must rebuild an area only if its start time is before its end time, both are within the time range of the open data files (LLFR-00911), and it does not overlap a current area or an area already rebuilt from the same layout file.

*Parent: HLFR-00050, HLFR-00052, HLFR-00088*

### LLFR-00725 Reason for an area not rebuilt
When loading a layout, the load report (LLFR-00237) must give the reason for each area that is not rebuilt (LLFR-00319).

*Parent: HLFR-00050, HLFR-00052, HLFR-00088*

### LLFR-00726 Missing area color in a layout
When loading a layout, a rebuilt area (LLFR-00319) whose saved color is missing must get the default color of LLFR-00731.

*Parent: HLFR-00050, HLFR-00052, HLFR-00088*

### LLFR-00727 Valid area color in a layout
When loading a layout, a saved area color (LLFR-00319) written as `#rrggbb`, with six hexadecimal digits in uppercase or lowercase, must be used as it is.

*Parent: HLFR-00050, HLFR-00052, HLFR-00088*

### LLFR-00728 Invalid area color in a layout
When loading a layout, an area (LLFR-00319) whose saved color is not written as `#rrggbb` must get the default color of LLFR-00731.

*Parent: HLFR-00050, HLFR-00052, HLFR-00088*

### LLFR-00729 Invalid area color in the load report
When loading a layout, the load report (LLFR-00237) must list each area whose saved color is not written as `#rrggbb` (LLFR-00728) as a replaced value (LLFR-00235).

*Parent: HLFR-00050, HLFR-00052, HLFR-00088*

### LLFR-00351 Choose an area color
When the user chooses "Color" in the area menu (LLFR-00314), the app must let the user choose a color (LLFR-00388, LLFR-00809, LLFR-00419).

*Parent: HLFR-00066, HLFR-00088*

### LLFR-00730 Area drawn in the chosen color
When the user chooses a color for an area (LLFR-00351), the app must draw that area in the chosen color (LLFR-00390) on every time plot of every tab (LLFR-00310).

*Parent: HLFR-00066, HLFR-00088*

### LLFR-00731 Default area color
Every new area must get the default color, the reserved marker color `#ff8000` (LLFR-00083).

*Parent: HLFR-00066, HLFR-00088*

### LLFR-00732 Same opacity for every area color
Whatever its color, an area must be drawn see-through with the same opacity (LLFR-00305), so that the curves, the grid and the other items stay visible (LLFR-00306).

*Parent: HLFR-00066, HLFR-00088*

### LLFR-00333 Start writing a text note
While the Text button (LLFR-00320) is active and the user left-clicks a plot's drawing area, on a time plot or a frequency plot, anywhere other than on an existing text note or pinned data tip, the app must show a one-line text field at the clicked point, with the keyboard focus in it, except as in LLFR-00886.

*Parent: HLFR-00073*

### LLFR-00733 Text field stays open
The text field of LLFR-00333 must stay open if the Text button is deactivated while the user types.

*Parent: HLFR-00073*

### LLFR-00334 Confirm a text note
When the user presses the Enter key or clicks outside the text field of LLFR-00333 and the text is not empty or made only of spaces, the app must create a text note with that text at the clicked point.

*Parent: HLFR-00073*

### LLFR-00734 Text field removed on confirm
When the user presses the Enter key or clicks outside the text field of LLFR-00333, the app must remove the field.

*Parent: HLFR-00073*

### LLFR-00735 Empty text note not created
When the user presses the Enter key or clicks outside the text field of LLFR-00333 and the text is empty or made only of spaces, the app must not create a text note.

*Parent: HLFR-00073*

### LLFR-00736 No message on an empty text note
When the user presses the Enter key or clicks outside the text field of LLFR-00333 and the text is empty or made only of spaces, the app must not show any message.

*Parent: HLFR-00073*

### LLFR-00335 Cancel a text note
When the user presses the Esc key in the text field of LLFR-00333, the app must remove the field.

*Parent: HLFR-00073*

### LLFR-00737 No text note on cancel
When the user presses the Esc key in the text field of LLFR-00333, the app must not create a text note.

*Parent: HLFR-00073*

### LLFR-00738 No message on cancel
When the user presses the Esc key in the text field of LLFR-00333, the app must not show any message.

*Parent: HLFR-00073*

### LLFR-00336 Text note appearance
The app must show a text note as its text on a white rounded box with a border, like a pinned data tip (LLFR-00045), with no other fill color, so that it is easy to read over the curves and the grid.

*Parent: HLFR-00073*

### LLFR-00739 Text note drawn in its colors
The app must draw the text of a text note (LLFR-00336) in the text note's text color and its border in its border color (LLFR-00387, LLFR-00808).

*Parent: HLFR-00073*

### LLFR-00740 New text note defaults
Every new text note must have the app's text color `#24303b`, a near-black dark grey, as its text color, the reserved orange `#ff8000` of LLFR-00083 as its border color, and the size of LLFR-00803.

*Parent: HLFR-00073*

### LLFR-00337 Text note follows its place
A text note must stay attached to its x-axis and y-axis values when the plot's x-axis or y-axis range or the plot's size changes.

*Parent: HLFR-00073*

### LLFR-00741 Text note hidden outside the range
A text note must be hidden while its x-axis or y-axis value (LLFR-00337) is outside the range shown in the plot.

*Parent: HLFR-00073*

### LLFR-00338 Text note kept inside the plot
While a text note is shown, the app must move it by the shortest distance needed to keep the whole text note inside the plot's drawing area.

*Parent: HLFR-00073, HLFR-00074*

### LLFR-00339 Drag a text note
When the user presses the left mouse button on a text note and drags it, the app must move the text note with the mouse pointer and leave it where the button is released, attached to the x-axis and y-axis values of that place.

*Parent: HLFR-00074, HLFR-00032*

### LLFR-00742 Press on a text note with any plot tool
A left mouse button press on a text note must start moving it (LLFR-00339) whether or not a plot tool is active.

*Parent: HLFR-00074, HLFR-00032*

### LLFR-00743 Press on a text note does nothing else
A left mouse button press on a text note (LLFR-00339) must not pin a data tip, move a pinned data tip, zoom, pan, place or move a flag, create, move or resize an area, draw, move, rotate or stretch an arrow, pick a delta marker point or start another text note.

*Parent: HLFR-00074, HLFR-00032*

### LLFR-00340 Text notes belong to one plot
A text note must be shown only on the plot where it was written.

*Parent: HLFR-00073*

### LLFR-00744 Text notes removed with their plot
A text note must be removed with the plot where it was written (LLFR-00049, LLFR-00051).

*Parent: HLFR-00073*

### LLFR-00745 Any number of text notes
A plot must be able to hold any number of text notes.

*Parent: HLFR-00073*

### LLFR-00341 Text note menu
When the user right-clicks a text note, the app must show a menu with the options "Edit", "Size", "Border color", "Text color" and "Delete", in this order, and not the menu of a curve, a flag, a delta marker, an area or an arrow under it.

*Parent: HLFR-00075, HLFR-00076, HLFR-00086, HLFR-00087*

### LLFR-00342 Edit a text note action
When the user chooses "Edit" in the text note menu (LLFR-00341), the app must let the user type a new text for that text note.

*Parent: HLFR-00075*

### LLFR-00746 Empty text note text
If the user enters a new text (LLFR-00342) that is empty or made only of spaces, the app must keep the text note's previous text.

*Parent: HLFR-00075*

### LLFR-00747 No message on an empty text note text
If the user enters a new text (LLFR-00342) that is empty or made only of spaces, the app must not show any message.

*Parent: HLFR-00075*

### LLFR-00748 Editing keeps size and colors
Editing the text of a text note (LLFR-00342) must not change the text note's size or colors (LLFR-00385, LLFR-00802, LLFR-00387, LLFR-00808).

*Parent: HLFR-00075*

### LLFR-00343 Delete a text note action
When the user chooses "Delete" in the text note menu (LLFR-00341), the app must remove that text note from the plot.

*Parent: HLFR-00076*

### LLFR-00344 DELETED
DELETED

### LLFR-00345 Pan by two-finger swipe
When the user swipes two fingers left or right on a trackpad or touchpad with the mouse pointer over a plot, the app must shift the plot's x-axis range in proportion to the movement, so that the curves follow the fingers horizontally, whether or not a plot tool is active and whatever the system's "natural scrolling" setting.

*Parent: HLFR-00036*

### LLFR-00749 Limits of the two-finger swipe pan
When the app pans a plot by a two-finger swipe (LLFR-00345), the limits and y-axis ranges of LLFR-00118 to LLFR-00120 must apply.

*Parent: HLFR-00036*

### LLFR-00346 Horizontal swipe only pans
A two-finger swipe that moves more horizontally than vertically must only pan (LLFR-00345), so that a swipe never does both a pan and a zoom.

*Parent: HLFR-00036, HLFR-00027*

### LLFR-00750 Other swipes only zoom
A two-finger swipe that does not move more horizontally than vertically must only zoom (LLFR-00074, LLFR-00659, LLFR-00206, LLFR-00672), so that a swipe never does both a pan and a zoom.

*Parent: HLFR-00036, HLFR-00027*

### LLFR-00352 Preview of a delta marker point
While the Delta X button (LLFR-00161) or the Delta Y button (LLFR-00162) is active, including while the X or Y key is held (LLFR-00197, LLFR-00200), and the mouse pointer is over a curve where a click would take a first point (LLFR-00163, LLFR-00166), the app must show a dot on the curve sample nearest to the pointer, in a paler version of the reserved marker color (LLFR-00083).

*Parent: HLFR-00043, HLFR-00044*

### LLFR-00751 Delta marker point preview follows the pointer
While the dot of LLFR-00352 is shown, the app must move it as the pointer moves.

*Parent: HLFR-00043, HLFR-00044*

### LLFR-00353 Preview of a delta marker
While a first point is picked (LLFR-00163) and the mouse pointer is over a curve in the same plot, the app must show a preview of the marker that a click would draw (LLFR-00164, LLFR-00682): a Delta X or Delta Y marker, according to the active button, between the first point and the curve sample nearest to the pointer, in a paler version of the reserved marker color, with its value (LLFR-00169, LLFR-00171, LLFR-00261) and without a label (LLFR-00427), except as in LLFR-00432.

*Parent: HLFR-00043, HLFR-00044*

### LLFR-00752 Delta marker preview follows the pointer
While the preview of LLFR-00353 is shown, the app must update it as the pointer moves, except as in LLFR-00432.

*Parent: HLFR-00043, HLFR-00044*

### LLFR-00354 Delta marker preview hidden
The app must hide the previews of LLFR-00352 and LLFR-00353 when the pointer is no longer over a curve or when the button is deactivated.

*Parent: HLFR-00043, HLFR-00044*

### LLFR-00753 Delta marker previews not exported
The previews of LLFR-00352 and LLFR-00353 must not appear in the PDF export (LLFR-00129) or the copied image (LLFR-00133).

*Parent: HLFR-00043, HLFR-00044*

### LLFR-00754 Delta marker previews not saved
The previews of LLFR-00352 and LLFR-00353 must not be saved in a layout file (LLFR-00225).

*Parent: HLFR-00043, HLFR-00044*

### LLFR-00755 Delta marker previews not undoable
The previews of LLFR-00352 and LLFR-00353 must not be undoable actions (LLFR-00140).

*Parent: HLFR-00043, HLFR-00044*

### LLFR-00756 First point dot kept when the previews hide
When the app hides the previews of LLFR-00352 and LLFR-00353 (LLFR-00354), it must keep the dot of a first point (LLFR-00165).

*Parent: HLFR-00043, HLFR-00044*

### LLFR-00356 Pan by left drag
While the Pan button (LLFR-00355) is active and the user presses the left mouse button on a plot's drawing area and moves the pointer, the app must shift the plot's x-axis range so that the curves follow the pointer horizontally.

*Parent: HLFR-00036*

### LLFR-00757 Limits of the left drag pan
When the app pans a plot by a left drag (LLFR-00356), the limits and y-axis ranges of LLFR-00118 to LLFR-00120 must apply.

*Parent: HLFR-00036*

### LLFR-00758 Time plots moved by the left drag pan
A pan by a left drag (LLFR-00356) on a time plot must apply to every time plot (LLFR-00070).

*Parent: HLFR-00036*

### LLFR-00759 Frequency plot moved by the left drag pan
A pan by a left drag (LLFR-00356) on a frequency plot must apply only to the plot it is used on (LLFR-00693).

*Parent: HLFR-00036*

### LLFR-00357 Pan tool moves data tips and text notes
While the Pan button (LLFR-00355) is active, a press on a pinned data tip or a text note must move it (LLFR-00153, LLFR-00339, LLFR-00742).

*Parent: HLFR-00036, HLFR-00032*

### LLFR-00760 No pan from a data tip or text note
While the Pan button (LLFR-00355) is active, a press on a pinned data tip or a text note must not pan.

*Parent: HLFR-00036, HLFR-00032*

### LLFR-00761 Pan from a flag, delta marker, area or arrow
While the Pan button (LLFR-00355) is active, a press on a flag, a delta marker, an area or an arrow must pan (LLFR-00798).

*Parent: HLFR-00036, HLFR-00032*

### LLFR-00762 Pan leaves the item unchanged
While the Pan button (LLFR-00355) is active, a press on a flag, a delta marker, an area or an arrow must not change that item (LLFR-00799).

*Parent: HLFR-00036, HLFR-00032*

### LLFR-00763 Click with the Pan button active
While the Pan button (LLFR-00355) is active, a left-click that does not move the pointer must do nothing.

*Parent: HLFR-00036, HLFR-00032*

### LLFR-00764 No message on a click with the Pan button active
While the Pan button (LLFR-00355) is active, a left-click that does not move the pointer must not show any message.

*Parent: HLFR-00036, HLFR-00032*

### LLFR-00371 Arrow preview while drawing
While the Arrow button (LLFR-00366) is active and the user presses the left mouse button on a plot's drawing area, on a time plot or a frequency plot, at a point that is not on an existing arrow, pinned data tip or text note, and moves the pointer 5 pixels or more from where the button was pressed, the app must show on that plot a preview of the arrow, from the point of the press to the point under the pointer, with its arrowhead at the pointer.

*Parent: HLFR-00081*

### LLFR-00765 Arrow preview follows the pointer
While the preview of LLFR-00371 is shown, the app must update it as the pointer moves.

*Parent: HLFR-00081*

### LLFR-00372 Create an arrow
When the user releases the left mouse button after LLFR-00371, the app must create an arrow from the point of the press to the point of the release, with its arrowhead at the point of the release, except as in LLFR-00768.

*Parent: HLFR-00081*

### LLFR-00766 Arrow preview removed on release
When the user releases the left mouse button after LLFR-00371, the app must remove the preview.

*Parent: HLFR-00081*

### LLFR-00767 Arrow released outside the drawing area
If the button of LLFR-00372 is released outside the plot's drawing area, the end of the arrow must be the nearest point of the drawing area.

*Parent: HLFR-00081*

### LLFR-00768 Short drag creates no arrow
When the user releases the left mouse button after LLFR-00371 less than 5 pixels from the press, the app must not create an arrow.

*Parent: HLFR-00081*

### LLFR-00769 No message on a short arrow drag
When the user releases the left mouse button after LLFR-00371 less than 5 pixels from the press, the app must not show any message.

*Parent: HLFR-00081*

### LLFR-00373 Arrow appearance
The app must draw an arrow as a straight dashed line with a filled arrowhead at its end, both in the arrow's color. A point is on an arrow when it is within 5 pixels of its line, on its arrowhead or on its label (LLFR-00436).

*Parent: HLFR-00081*

### LLFR-00770 Default arrow color
Every new arrow must have the reserved orange `#ff8000` of LLFR-00083 until the user chooses another color (LLFR-00379).

*Parent: HLFR-00081*

### LLFR-00771 Arrow drawing order
The app must draw arrows above the curves, the grid, the areas, the flags and the delta markers, and below the pinned data tips and the text notes.

*Parent: HLFR-00081*

### LLFR-00772 Arrow preview color
The previews of LLFR-00371, LLFR-00779 and LLFR-00782 must be drawn in a paler version of the arrow's color.

*Parent: HLFR-00081*

### LLFR-00773 Arrow previews not exported
The previews of LLFR-00371, LLFR-00779 and LLFR-00782 must not appear in the PDF export (LLFR-00129) or the copied image (LLFR-00133).

*Parent: HLFR-00081*

### LLFR-00774 No label on the drawing preview
The preview of LLFR-00371 must not show a label.

*Parent: HLFR-00081*

### LLFR-00374 Arrow follows its ends
An arrow must stay attached to the x-axis and y-axis values of its two ends when the plot's x-axis or y-axis range or the plot's size changes.

*Parent: HLFR-00081*

### LLFR-00775 Arrow cut at the plot edge
When a part of an arrow is outside the shown ranges, the app must draw only the part inside the plot's drawing area, cut at its edge.

*Parent: HLFR-00081*

### LLFR-00776 Arrowhead of a partly shown arrow
When a part of an arrow is outside the shown ranges, the app must draw the arrowhead only while the end that holds it is shown.

*Parent: HLFR-00081*

### LLFR-00375 Arrows belong to one plot
An arrow must be shown only on the plot where it was drawn.

Note: Arrows behave like text notes in this (LLFR-00340).

*Parent: HLFR-00081*

### LLFR-00777 Arrows removed with their plot
An arrow must be removed with the plot where it was drawn (LLFR-00049, LLFR-00051).

Note: Arrows behave like text notes in this (LLFR-00744).

*Parent: HLFR-00081*

### LLFR-00778 Any number of arrows
A plot must be able to hold any number of arrows.

Note: Arrows behave like text notes in this (LLFR-00745).

*Parent: HLFR-00081*

### LLFR-00376 Move an arrow
While the Arrow button (LLFR-00366) is active or no plot tool is active (LLFR-00793), and the user presses the left mouse button on an arrow (LLFR-00373) more than 5 pixels from both of its ends and drags, the app must move the arrow, when the button is released, to the place of the preview of LLFR-00779, keeping its length and direction, attached to the x-axis and y-axis values of its new ends, except as in LLFR-00781.

*Parent: HLFR-00082*

### LLFR-00779 Arrow move preview
While the user drags an arrow as in LLFR-00376, the app must show a preview of the arrow moved with the mouse pointer, keeping its length and direction.

*Parent: HLFR-00082*

### LLFR-00780 Moved arrow released outside the drawing area
If the button of LLFR-00376 is released outside the plot's drawing area, the app must use the nearest point of the drawing area as the point of the release.

*Parent: HLFR-00082*

### LLFR-00781 Short drag does not move an arrow
In the drag of LLFR-00376, a release less than 5 pixels from the press must not move the arrow.

*Parent: HLFR-00082*

### LLFR-00377 Rotate and stretch an arrow
While the Arrow button (LLFR-00366) is active or no plot tool is active (LLFR-00793), and the user presses the left mouse button within 5 pixels of one end of an arrow and drags, the app must give the arrow, when the button is released, the shape of the preview of LLFR-00782, except as in LLFR-00787.

*Parent: HLFR-00083*

### LLFR-00782 Rotate and stretch preview
While the user drags an end of an arrow as in LLFR-00377, the app must show a preview of the arrow with that end at the mouse pointer and the other end in place, so that the arrow turns around the end that was not pressed and gets longer or shorter.

*Parent: HLFR-00083*

### LLFR-00783 Press near both ends of an arrow
When the press of LLFR-00377 is within 5 pixels of both ends of the arrow, the nearer end must move.

*Parent: HLFR-00083*

### LLFR-00784 Minimum arrow length
In the drag of LLFR-00377, the moved end must stay at least 5 pixels from the other end.

*Parent: HLFR-00083*

### LLFR-00785 Arrow end released outside the drawing area
If the button of LLFR-00377 is released outside the plot's drawing area, the moved end must be the nearest point of the drawing area.

*Parent: HLFR-00083*

### LLFR-00786 Arrowhead stays at its end
When the user rotates or stretches an arrow (LLFR-00377), the arrowhead must stay at the same end of the arrow.

*Parent: HLFR-00083*

### LLFR-00787 Short drag does not change an arrow
In the drag of LLFR-00377, a release less than 5 pixels from the press must not change the arrow.

*Parent: HLFR-00083*

### LLFR-00378 Arrow menu
When the user right-clicks an arrow, the app must show a menu with the options "Rename", "Color" and "Delete", in this order.

*Parent: HLFR-00084, HLFR-00088, HLFR-00100, HLFR-00111*

### LLFR-00379 Arrow color action
When the user chooses "Color" in the arrow menu (LLFR-00378), the app must let the user choose a color (LLFR-00388, LLFR-00809, LLFR-00419).

*Parent: HLFR-00088*

### LLFR-00788 Arrow drawn in the chosen color
When the user chooses a color for an arrow (LLFR-00379), the app must draw the arrow's line, arrowhead and label (LLFR-00436) in the chosen color (LLFR-00390).

*Parent: HLFR-00088*

### LLFR-00380 Delete an arrow action
When the user chooses "Delete" in the arrow menu (LLFR-00378), the app must remove that arrow from the plot.

*Parent: HLFR-00084*

### LLFR-00381 Menus over an arrow
When the user right-clicks a point on an arrow (LLFR-00373) where a curve, a flag, a delta marker or an area is also drawn, the app must show the arrow menu (LLFR-00378) and not the menu of that item, except as in LLFR-00789.

*Parent: HLFR-00084, HLFR-00088*

### LLFR-00789 Data tip and text note menus over an arrow
When the user right-clicks a point on an arrow (LLFR-00373) where a pinned data tip or a text note is drawn over the arrow, the app must show the menu of the data tip (LLFR-00046) or of the text note (LLFR-00341) and not the arrow menu.

*Parent: HLFR-00084, HLFR-00088*

### LLFR-00382 Drag a flag with no plot tool active
While no plot tool is active, a left mouse button press and drag on a flag must move it (LLFR-00086).

*Parent: HLFR-00085, HLFR-00029*

### LLFR-00790 Drag an area with no plot tool active
While no plot tool is active, a left mouse button press and drag on an area must move it (LLFR-00312) or resize it (LLFR-00313).

*Parent: HLFR-00085, HLFR-00067, HLFR-00106*

### LLFR-00791 Drag a pinned data tip with no plot tool active
While no plot tool is active, a left mouse button press and drag on a pinned data tip must move it (LLFR-00152).

*Parent: HLFR-00085, HLFR-00041*

### LLFR-00792 Drag a text note with no plot tool active
While no plot tool is active, a left mouse button press and drag on a text note must move it (LLFR-00339).

*Parent: HLFR-00085, HLFR-00074*

### LLFR-00793 Drag an arrow with no plot tool active
While no plot tool is active, a left mouse button press and drag on an arrow must move it (LLFR-00376) or rotate and stretch it (LLFR-00377).

*Parent: HLFR-00085, HLFR-00082, HLFR-00083*

### LLFR-00794 Drag a delta marker point with no plot tool active
While no plot tool is active, a left mouse button press and drag on one of the two dots of a delta marker must move that point (LLFR-00433).

*Parent: HLFR-00085, HLFR-00099*

### LLFR-00795 Drag elsewhere with no plot tool active
While no plot tool is active, a left mouse button press and drag on the rest of a delta marker, on a curve or on a part of a plot where none of the objects of LLFR-00382, LLFR-00790, LLFR-00791, LLFR-00792, LLFR-00793 and LLFR-00794 is drawn must do nothing.

*Parent: HLFR-00085, HLFR-00099*

### LLFR-00796 No message on a drag elsewhere with no plot tool active
While no plot tool is active, a left mouse button press and drag on the rest of a delta marker, on a curve or on a part of a plot where none of the objects of LLFR-00382, LLFR-00790, LLFR-00791, LLFR-00792, LLFR-00793 and LLFR-00794 is drawn must not show any message.

*Parent: HLFR-00085, HLFR-00099*

### LLFR-00383 Order of the objects at one point
When the user presses the left mouse button at a point where several objects that react to the press are drawn (LLFR-00382, LLFR-00790, LLFR-00791, LLFR-00792, LLFR-00793, LLFR-00794, LLFR-00384, LLFR-00800, LLFR-00801), the app must act only on the first of them in this order: text note, pinned data tip, arrow, delta marker point, flag, area.

*Parent: HLFR-00085, HLFR-00032*

### LLFR-00797 Same kind of objects at one point
Among the objects of LLFR-00383 at the point of the press that are of the same kind, the app must act on the one drawn last.

*Parent: HLFR-00085, HLFR-00032*

### LLFR-00384 Objects of the active plot tool
While a plot tool is active, a press on a flag, an area or an arrow must edit that object only when the active tool is its own: the Flag button for flags (LLFR-00086), the Area button for areas (LLFR-00312, LLFR-00313) and the Arrow button for arrows (LLFR-00376, LLFR-00377).

*Parent: HLFR-00085, HLFR-00032*

### LLFR-00798 Other plot tools act as where no object is drawn
While a plot tool is active, with any plot tool other than the own tool of LLFR-00384, a press on a flag, an area or an arrow must act as the active tool does where no object is drawn, except as in LLFR-00886; for example, with the Zoom button active, a press on a flag zooms (LLFR-00318, LLFR-00761).

*Parent: HLFR-00085, HLFR-00032*

### LLFR-00799 Other plot tools leave the object unchanged
While a plot tool is active, with any plot tool other than the own tool of LLFR-00384, a press on a flag, an area or an arrow must not change the object.

*Parent: HLFR-00085, HLFR-00032*

### LLFR-00800 Data tips and text notes move with any plot tool
While a plot tool is active, pinned data tips and text notes must move with any plot tool (LLFR-00153, LLFR-00339, LLFR-00742).

*Parent: HLFR-00085, HLFR-00032*

### LLFR-00801 Delta marker points move only with the delta tools
While a plot tool is active, the points of a delta marker must move only with the Delta X or the Delta Y button (LLFR-00433).

*Parent: HLFR-00085, HLFR-00032*

### LLFR-00385 Text note size option
When the user chooses "Size" in the text note menu (LLFR-00341), the app must list the sizes 8, 10, 12, 16, 20, 24 and 32 points, with the text note's chosen size shown as chosen.

*Parent: HLFR-00086*

### LLFR-00802 Text note size applied
When the user chooses a size in the list of LLFR-00385, the app must draw the text note's text at the size the user chooses.

*Parent: HLFR-00086*

### LLFR-00803 Default text note size
Every new text note must have the size 12 points.

*Parent: HLFR-00086*

### LLFR-00386 Text note height limit
The app must never draw a text note, with its box, taller than 25% of the height of its plot's drawing area.

*Parent: HLFR-00086*

### LLFR-00804 Text note drawn smaller to fit
When the chosen size of a text note (LLFR-00385, LLFR-00802) would make it taller than the limit of LLFR-00386, the app must draw it at the largest size at which it fits.

*Parent: HLFR-00086*

### LLFR-00805 Text note size when the plot grows
When the plot of a text note drawn as in LLFR-00804 grows again, the app must draw the text note again at its chosen size, or at the largest size that fits if the chosen size still does not.

*Parent: HLFR-00086*

### LLFR-00806 Chosen text note size kept
When the app draws a text note at a smaller size than its chosen size (LLFR-00804, LLFR-00805), the chosen size must not change.

*Parent: HLFR-00086*

### LLFR-00807 Size option shows the chosen size
When the app draws a text note at a smaller size than its chosen size (LLFR-00804, LLFR-00805), the Size option (LLFR-00385) must keep showing the chosen size as chosen.

*Parent: HLFR-00086*

### LLFR-00387 Text note color options
When the user chooses "Border color" or "Text color" in the text note menu (LLFR-00341), the app must let the user choose a color (LLFR-00388, LLFR-00809, LLFR-00419).

*Parent: HLFR-00087, HLFR-00088*

### LLFR-00808 Text note drawn in the chosen colors
When the user chooses a color with "Border color" or "Text color" (LLFR-00387), the app must draw the text note's border or its text, respectively, in the chosen color (LLFR-00390).

*Parent: HLFR-00087, HLFR-00088*

### LLFR-00388 Shared color submenu
The "Color" options of the arrow menu (LLFR-00379), the flag menu (LLFR-00391), the area menu (LLFR-00351) and the delta marker menu (LLFR-00409), and the "Border color" and "Text color" options of the text note menu (LLFR-00387), must each open a submenu with the recent colors (LLFR-00419) followed by an "Other color..." option.

*Parent: HLFR-00088*

### LLFR-00809 Shared color picker
Choosing "Other color..." in the submenu of LLFR-00388 must open the color picker window, the same for all the options of LLFR-00388.

*Parent: HLFR-00088*

### LLFR-00810 Any opaque color in the color picker
The color picker window of LLFR-00809 must let the user choose any opaque color, with any red, green and blue values from 0 to 255.

*Parent: HLFR-00088*

### LLFR-00389 Color picker starting color
When the color picker (LLFR-00809) opens, it must show as chosen the current color of the item, or of its border or its text for the "Border color" and "Text color" options of a text note.

*Parent: HLFR-00088*

### LLFR-00390 Color picker confirm
When the user confirms a color in the color picker (LLFR-00809) or chooses a recent color (LLFR-00419), the app must apply it to the item as one undoable action (LLFR-00140), except as in LLFR-00811 and LLFR-00812.

*Parent: HLFR-00088, HLFR-00040*

### LLFR-00811 Color picker cancelled or same color
When the user cancels the color picker (LLFR-00809), closes the submenu of LLFR-00388 without choosing an option, or confirms or chooses the color the item already has, the app must change nothing.

*Parent: HLFR-00088, HLFR-00040*

### LLFR-00812 No undoable action without a color change
When the user cancels the color picker (LLFR-00809), closes the submenu of LLFR-00388 without choosing an option, or confirms or chooses the color the item already has, the app must not add an undoable action.

*Parent: HLFR-00088, HLFR-00040*

### LLFR-00391 Flag color option
When the user right-clicks a flag, the app must show a "Color" option in the flag menu, between the "Rename" option (LLFR-00087) and the "Delete" option (LLFR-00090).

*Parent: HLFR-00089, HLFR-00088*

### LLFR-00392 Flag color action
When the user chooses "Color" in the flag menu (LLFR-00391), the app must let the user choose a color (LLFR-00388, LLFR-00809, LLFR-00419).

*Parent: HLFR-00089, HLFR-00088*

### LLFR-00813 Flag drawn in the chosen color
When the user chooses a color for a flag (LLFR-00392), the app must draw the flag's line, the text of its name label (LLFR-00084) and its time value (LLFR-00092) in the chosen color (LLFR-00390), on every time plot of every tab (LLFR-00205, LLFR-00664).

*Parent: HLFR-00089, HLFR-00088*

### LLFR-00393 Flag colors in a layout
When loading a layout, the app must give each rebuilt flag (LLFR-00233) its saved color (LLFR-00225), except as in LLFR-00815 and LLFR-00816.

*Parent: HLFR-00050, HLFR-00052, HLFR-00089*

### LLFR-00814 Hexadecimal flag colors in a layout
When loading a layout, a saved flag color written as `#rrggbb`, with six hexadecimal digits in uppercase or lowercase, must be used as it is.

*Parent: HLFR-00050, HLFR-00052, HLFR-00089*

### LLFR-00815 Missing flag color in a layout
When loading a layout, a flag whose saved color is missing must get the default color of LLFR-00083.

*Parent: HLFR-00050, HLFR-00052, HLFR-00089*

### LLFR-00816 Unusable flag color in a layout
When loading a layout, a flag whose saved color is not written as `#rrggbb` must get the default color of LLFR-00083.

*Parent: HLFR-00050, HLFR-00052, HLFR-00089*

### LLFR-00817 Unusable flag color in the load report
When loading a layout, the load report (LLFR-00237) must list a flag of LLFR-00816 as a replaced value (LLFR-00235).

*Parent: HLFR-00050, HLFR-00052, HLFR-00089*

### LLFR-00409 Delta marker color action
When the user chooses "Color" in the delta marker menu (LLFR-00175), the app must let the user choose a color (LLFR-00388, LLFR-00809, LLFR-00419).

*Parent: HLFR-00092, HLFR-00088*

### LLFR-00818 Delta marker drawn in the chosen color
When the user chooses a color for a delta marker (LLFR-00409), the app must draw the delta marker's curly bracket, both of its dots, its value text (LLFR-00169, LLFR-00171, LLFR-00261) and its label (LLFR-00427) in the chosen color (LLFR-00390).

*Parent: HLFR-00092, HLFR-00088*

### LLFR-00819 Delta marker color keeps its points
Changing the color of a delta marker (LLFR-00409) must not change the delta marker's points or value.

*Parent: HLFR-00092, HLFR-00088*

### LLFR-00820 Delta marker color keeps the other markers
Changing the color of a delta marker (LLFR-00409) must not change the color of any other delta marker.

*Parent: HLFR-00092, HLFR-00088*

### LLFR-00410 Delta marker colors in a layout
When loading a layout, the app must give each rebuilt delta marker (LLFR-00232) its saved color (LLFR-00225), except as in LLFR-00822 and LLFR-00823.

Note: A layout file saved before delta markers had a color has no color for them, so they get the default color and nothing is reported. Adding the delta marker colors did not change the layout file `version` (LLFR-00471).

*Parent: HLFR-00050, HLFR-00052, HLFR-00092*

### LLFR-00821 Hexadecimal delta marker colors in a layout
When loading a layout, a saved delta marker color written as `#rrggbb`, with six hexadecimal digits in uppercase or lowercase, must be used as it is.

*Parent: HLFR-00050, HLFR-00052, HLFR-00092*

### LLFR-00822 Missing delta marker color in a layout
When loading a layout, a delta marker whose saved color is missing must get the default color of LLFR-00172.

Note: A layout file saved before delta markers had a color has no color for them, so they get the default color and nothing is reported.

*Parent: HLFR-00050, HLFR-00052, HLFR-00092*

### LLFR-00823 Unusable delta marker color in a layout
When loading a layout, a delta marker whose saved color is not written as `#rrggbb` must get the default color of LLFR-00172.

*Parent: HLFR-00050, HLFR-00052, HLFR-00092*

### LLFR-00824 Unusable delta marker color in the load report
When loading a layout, the load report (LLFR-00237) must list a delta marker of LLFR-00823 as a replaced value (LLFR-00235).

*Parent: HLFR-00050, HLFR-00052, HLFR-00092*

### LLFR-00411 Double-click a text note
When the user double-clicks a text note with the left mouse button, whether a plot tool is active or not, the app must act as when the user chooses "Edit" in the text note menu (LLFR-00342, LLFR-00746, LLFR-00747, LLFR-00748).

*Parent: HLFR-00075*

### LLFR-00825 Double-click on a text note does nothing else
When the user double-clicks a text note with the left mouse button, whether a plot tool is active or not, the app must not pin a data tip, zoom, pan, place a flag, create an area, start another text note, draw an arrow, pick a delta marker point, create a plot or do anything else besides LLFR-00411.

*Parent: HLFR-00075*

### LLFR-00412 Delete all data tips in this plot
When the user chooses "Delete all data tips in this plot" in the pinned data tip menu (LLFR-00046), the app must remove every pinned data tip of that plot, as one undoable action (LLFR-00140).

*Parent: HLFR-00093, HLFR-00025*

### LLFR-00826 Other plots keep their data tips
When the user chooses "Delete all data tips in this plot" (LLFR-00412), the pinned data tips of the other plots must not change.

*Parent: HLFR-00093, HLFR-00025*

### LLFR-00827 No confirmation for "Delete all data tips in this plot"
When the user chooses "Delete all data tips in this plot" (LLFR-00412), the app must not ask for confirmation.

*Parent: HLFR-00093, HLFR-00025*

### LLFR-00877 No message for "Delete all data tips in this plot"
When the user chooses "Delete all data tips in this plot" (LLFR-00412), the app must not show any message.

*Parent: HLFR-00093, HLFR-00025*

### LLFR-00413 Delete all data tips in all plots
When the user chooses "Delete all data tips in all plots" in the pinned data tip menu (LLFR-00046), the app must remove every pinned data tip of every plot, time plot or frequency plot, in every tab, as one undoable action (LLFR-00140).

*Parent: HLFR-00093, HLFR-00025*

### LLFR-00828 No confirmation for "Delete all data tips in all plots"
When the user chooses "Delete all data tips in all plots" (LLFR-00413), the app must not ask for confirmation.

*Parent: HLFR-00093, HLFR-00025*

### LLFR-00878 No message for "Delete all data tips in all plots"
When the user chooses "Delete all data tips in all plots" (LLFR-00413), the app must not show any message.

*Parent: HLFR-00093, HLFR-00025*

### LLFR-00414 Delete all delta markers in this plot
When the user chooses "Delete all delta markers in this plot" in the delta marker menu (LLFR-00175), the app must remove every Delta X marker and every Delta Y marker of that plot, as one undoable action (LLFR-00140).

*Parent: HLFR-00093, HLFR-00043, HLFR-00044*

### LLFR-00829 Other plots keep their delta markers
When the user chooses "Delete all delta markers in this plot" (LLFR-00414), the delta markers of the other plots must not change.

*Parent: HLFR-00093, HLFR-00043, HLFR-00044*

### LLFR-00830 First point kept when deleting the delta markers of a plot
When the user chooses "Delete all delta markers in this plot" (LLFR-00414), a first point picked in any plot (LLFR-00163) must not change.

*Parent: HLFR-00093, HLFR-00043, HLFR-00044*

### LLFR-00831 No confirmation for "Delete all delta markers in this plot"
When the user chooses "Delete all delta markers in this plot" (LLFR-00414), the app must not ask for confirmation.

*Parent: HLFR-00093, HLFR-00043, HLFR-00044*

### LLFR-00879 No message for "Delete all delta markers in this plot"
When the user chooses "Delete all delta markers in this plot" (LLFR-00414), the app must not show any message.

*Parent: HLFR-00093, HLFR-00043, HLFR-00044*

### LLFR-00415 Delete all delta markers in all plots
When the user chooses "Delete all delta markers in all plots" in the delta marker menu (LLFR-00175), the app must remove every Delta X marker and every Delta Y marker of every plot, time plot or frequency plot, in every tab, as one undoable action (LLFR-00140).

*Parent: HLFR-00093, HLFR-00043, HLFR-00044*

### LLFR-00832 First point kept when deleting all delta markers
When the user chooses "Delete all delta markers in all plots" (LLFR-00415), a first point picked in any plot (LLFR-00163) must not change.

*Parent: HLFR-00093, HLFR-00043, HLFR-00044*

### LLFR-00833 No confirmation for "Delete all delta markers in all plots"
When the user chooses "Delete all delta markers in all plots" (LLFR-00415), the app must not ask for confirmation.

*Parent: HLFR-00093, HLFR-00043, HLFR-00044*

### LLFR-00880 No message for "Delete all delta markers in all plots"
When the user chooses "Delete all delta markers in all plots" (LLFR-00415), the app must not show any message.

*Parent: HLFR-00093, HLFR-00043, HLFR-00044*

### LLFR-00416 Delete all flags
When the user chooses "Delete all flags" in the flag menu (LLFR-00090), the app must remove every flag, with its label and time value, from every time plot in every tab (LLFR-00205), as one undoable action (LLFR-00140).

*Parent: HLFR-00093, HLFR-00031*

### LLFR-00834 No confirmation for "Delete all flags"
When the user chooses "Delete all flags" (LLFR-00416), the app must not ask for confirmation.

*Parent: HLFR-00093, HLFR-00031*

### LLFR-00881 No message for "Delete all flags"
When the user chooses "Delete all flags" (LLFR-00416), the app must not show any message.

*Parent: HLFR-00093, HLFR-00031*

### LLFR-00417 Delete all areas
When the user chooses "Delete all areas" in the area menu (LLFR-00314), the app must remove every area, with its label and time values, from every time plot in every tab (LLFR-00310), as one undoable action (LLFR-00140).

*Parent: HLFR-00093, HLFR-00069*

### LLFR-00835 No confirmation for "Delete all areas"
When the user chooses "Delete all areas" (LLFR-00417), the app must not ask for confirmation.

*Parent: HLFR-00093, HLFR-00069*

### LLFR-00882 No message for "Delete all areas"
When the user chooses "Delete all areas" (LLFR-00417), the app must not show any message.

*Parent: HLFR-00093, HLFR-00069*

### LLFR-00419 Recent colors
The submenu of LLFR-00388 must list, before "Other color...", the last 8 different colors that the user confirmed in the color picker or chose from this list, for any item, most recent first and with no color listed twice.

Note: Default colors given by the app (LLFR-00083, LLFR-00172, LLFR-00740, LLFR-00731, LLFR-00770) and colors read from a layout file are not added to the list. This list replaces saving custom colors in the system's color window, which does not work in the app on macOS.

*Parent: HLFR-00088*

### LLFR-00836 Recent color entries
Each entry of the recent colors (LLFR-00419) must show a small square swatch filled with its color, with the color's `#rrggbb` code next to it.

*Parent: HLFR-00088*

### LLFR-00837 Choose a recent color
Choosing an entry of the recent colors (LLFR-00419) must apply its color to the item as in LLFR-00390.

*Parent: HLFR-00088*

### LLFR-00838 Recent colors update
Each time the user confirms or chooses a color, including the color the item already has, the app must put that color first in the list of LLFR-00419, remove it from any later place, and keep only the first 8 colors.

Note: Default colors given by the app (LLFR-00083, LLFR-00172, LLFR-00740, LLFR-00731, LLFR-00770) and colors read from a layout file are not added to the list.

*Parent: HLFR-00088*

### LLFR-00839 Recent colors shared
The list of LLFR-00419 must be shared by all the color options of LLFR-00388.

*Parent: HLFR-00088*

### LLFR-00840 Recent colors kept between launches
The list of LLFR-00419 must be kept between launches in the app's settings.

*Parent: HLFR-00088*

### LLFR-00841 No recent colors
While the list of LLFR-00419 is empty, for example at the first launch or when the settings cannot be read, the submenu of LLFR-00388 must show only "Other color...".

*Parent: HLFR-00088*

### LLFR-00420 Double-click a label
When the user double-clicks with the left mouse button the name in the label of a flag (LLFR-00084), of an area (LLFR-00307), of a delta marker (LLFR-00427) or of an arrow (LLFR-00436), whether a plot tool is active or not, the app must act as when the user chooses "Rename" in the menu of that object (LLFR-00088, LLFR-00315, LLFR-00718, LLFR-00719, LLFR-00720, LLFR-00429, LLFR-00853, LLFR-00854, LLFR-00855, LLFR-00856, LLFR-00439, LLFR-00873, LLFR-00874, LLFR-00875, LLFR-00876).

*Parent: HLFR-00094*

### LLFR-00842 Double-click on a label does nothing else
When the user double-clicks with the left mouse button the name in the label of a flag, an area, a delta marker or an arrow (LLFR-00420), whether a plot tool is active or not, the app must not pin a data tip, zoom, pan, place a flag, create an area, start a text note, draw an arrow, pick a delta marker point, create a plot or do anything else besides LLFR-00420.

*Parent: HLFR-00094*

### LLFR-00886 Single click on a name label
When the user presses and releases the left mouse button less than 5 pixels apart on the name in the label of a flag, an area, a delta marker or an arrow (LLFR-00420), whether a plot tool is active or not, the app must leave the plot unchanged, so that the double-click of LLFR-00842 changes only the name.

Note: A press on the name followed by a drag of 5 pixels or more still acts as the active tool does, for example a time span selection with the Zoom button (LLFR-00208), a pan with the Pan button (LLFR-00356), or a move of the object with its own tool or with no tool (LLFR-00384, LLFR-00382).

*Parent: HLFR-00094*

### LLFR-00421 Double-click a tab
When the user double-clicks a tab with the left mouse button, the app must act as when the user chooses "Rename" in the tab menu (LLFR-00030, LLFR-00067, LLFR-00656, LLFR-00211, LLFR-00657, LLFR-00658).

*Parent: HLFR-00094, HLFR-00017*

### LLFR-00422 Values are not renamed
A double-click on the time value of a flag (LLFR-00092), on the times of an area (LLFR-00308) or on the value of a delta marker (LLFR-00169, LLFR-00171, LLFR-00261) must not let the user type.

*Parent: HLFR-00107*

### LLFR-00843 Double-click changes no value
A double-click on the time value of a flag (LLFR-00092), on the times of an area (LLFR-00308) or on the value of a delta marker (LLFR-00169, LLFR-00171, LLFR-00261) must not change any value.

*Parent: HLFR-00107*

### LLFR-00844 Values change only by moving
The values of LLFR-00422 must change only by moving the object: a flag (LLFR-00086), an area (LLFR-00312, LLFR-00313) or a point of a delta marker (LLFR-00433).

*Parent: HLFR-00107*

### LLFR-00423 Data tip text alignment
The app must align all the text inside a hover data tip (LLFR-00042) and a pinned data tip (LLFR-00045) to the left.

*Parent: HLFR-00024, HLFR-00025*

### LLFR-00425 Title of the plot menus
The menus of a curve (LLFR-00038, LLFR-00040), a pinned data tip (LLFR-00046), a plot (LLFR-00048), a flag (LLFR-00087), a delta marker (LLFR-00175), an area (LLFR-00314), a text note (LLFR-00341) and an arrow (LLFR-00378) must show a title above their first option.

*Parent: HLFR-00096*

### LLFR-00845 Separator below the menu title
The menus of LLFR-00425 must show a separator line between the title and the options.

*Parent: HLFR-00096*

### LLFR-00846 Look of the menu title
The title of LLFR-00425 must be drawn in bold and in a paler color than the options.

*Parent: HLFR-00096, HLFR-00108*

### LLFR-00847 Clicking the menu title does nothing
Clicking the title of LLFR-00425 must do nothing.

*Parent: HLFR-00096, HLFR-00109*

### LLFR-00848 Clicking the menu title keeps the menu open
Clicking the title of LLFR-00425 must not close the menu.

*Parent: HLFR-00096, HLFR-00109*

### LLFR-00849 Menu title not highlighted
The title of LLFR-00425 must not be highlighted by the mouse pointer or by the keyboard.

*Parent: HLFR-00096, HLFR-00108, HLFR-00109*

### LLFR-00426 Text of the menu title
The title of LLFR-00425 must be the name of the object the menu acts on:

| Menu | Title |
|---|---|
| Curve | The name of its signal |
| Pinned data tip | The name of the signal of its point |
| Flag, area, delta marker, arrow | Its name |
| Text note | Its text |
| Plot | "Plot" |

*Parent: HLFR-00096*

### LLFR-00850 Long menu titles
When the title of LLFR-00426 has more than 40 characters, the app must shorten it with "..." in the middle.

*Parent: HLFR-00096*

### LLFR-00427 Delta marker label
The app must show the name of a delta marker in a label directly above its value (LLFR-00169, LLFR-00171, LLFR-00261), in the delta marker's color (LLFR-00172, LLFR-00818).

Note: The label appears wherever the delta marker appears, including the PDF export (LLFR-00129) and the copied image (LLFR-00133).

*Parent: HLFR-00097*

### LLFR-00428 Default delta marker name
The app must name each new Delta X marker "Delta X N" and each new Delta Y marker "Delta Y N", where N is 1 for the first marker of that kind placed after the app starts and grows by 1 for each new marker of that kind, except as in LLFR-00852.

*Parent: HLFR-00097*

### LLFR-00851 Delta marker numbers not reused
The app must not reuse the number of a deleted delta marker (LLFR-00428), even when the marker's placement is undone, while the app runs.

*Parent: HLFR-00097*

### LLFR-00852 New delta marker name not in use
When the app names a new delta marker (LLFR-00428), it must skip every number whose name another delta marker of that kind already has.

*Parent: HLFR-00097*

### LLFR-00429 Rename delta marker action
When the user chooses "Rename" in the delta marker menu (LLFR-00175), the app must let the user type a new name for that delta marker.

*Parent: HLFR-00110*

### LLFR-00853 Renamed delta marker label
After the user types a new delta marker name (LLFR-00429), the app must show it in the delta marker's label (LLFR-00427), except as in LLFR-00854.

*Parent: HLFR-00097, HLFR-00110*

### LLFR-00854 Empty delta marker name
If the user enters a delta marker name (LLFR-00429) that is empty or made only of spaces, the app must keep the previous name.

*Parent: HLFR-00110*

### LLFR-00855 No message on an empty delta marker name
If the user enters a delta marker name (LLFR-00429) that is empty or made only of spaces, the app must not show any message.

*Parent: HLFR-00110*

### LLFR-00856 Renaming keeps the delta marker
Renaming a delta marker (LLFR-00429) must not change the delta marker's points, value or color.

*Parent: HLFR-00110*

### LLFR-00430 Delta marker names in a layout
When loading a layout, the app must give each rebuilt delta marker (LLFR-00232) its saved name (LLFR-00225), except as in LLFR-00857 and LLFR-00858.

Note: A layout file saved before delta markers had a name has no name for them, so they get a default name and nothing is reported.

*Parent: HLFR-00050, HLFR-00052, HLFR-00097*

### LLFR-00857 Missing delta marker name in a layout
When loading a layout, a delta marker whose saved name is missing must get a name as in LLFR-00428, LLFR-00851 and LLFR-00852.

Note: A layout file saved before delta markers had a name has no name for them, so they get a default name and nothing is reported.

*Parent: HLFR-00050, HLFR-00052, HLFR-00097*

### LLFR-00858 Unusable delta marker name in a layout
When loading a layout, a delta marker whose saved name is empty or not a text must get a name as in LLFR-00428, LLFR-00851 and LLFR-00852.

*Parent: HLFR-00050, HLFR-00052, HLFR-00097*

### LLFR-00859 Unusable delta marker name in the load report
When loading a layout, the load report (LLFR-00237) must list a delta marker of LLFR-00858 as a replaced value (LLFR-00235).

*Parent: HLFR-00050, HLFR-00052, HLFR-00097*

### LLFR-00431 Second point that gives zero
If the second point of LLFR-00164 gives a value of zero, because it has exactly the same time (frequency, on a frequency plot) as the first point for a Delta X marker, or exactly the same y-axis value as the first point for a Delta Y marker, the app must not draw the marker.

*Parent: HLFR-00098*

### LLFR-00860 First point kept after a zero value
If the second point of LLFR-00164 gives a value of zero (LLFR-00431), the app must keep the first point and its dot.

*Parent: HLFR-00098*

### LLFR-00861 No message on a zero value
If the second point of LLFR-00164 gives a value of zero (LLFR-00431), the app must not show any message.

*Parent: HLFR-00098*

### LLFR-00432 No preview of a zero value
While a first point is picked (LLFR-00163) and the curve sample nearest to the pointer would give a value of zero (LLFR-00431), the app must hide the whole delta marker preview: the preview of LLFR-00353 and the dot on that curve sample.

*Parent: HLFR-00098*

### LLFR-00433 Drag a delta marker point
While the Delta X button (LLFR-00161) or the Delta Y button (LLFR-00162) is active, or no plot tool is active (LLFR-00794), and the user presses the left mouse button on one of the two dots of a delta marker and moves the pointer 5 pixels or more from where the button was pressed, the app must move that point along its curve to the sample nearest to the time (the frequency, on a frequency plot) under the pointer, and leave it on the sample chosen when the button is released, limited to the x-axis range shown in the plot.

Note: A drag that leaves the point on the sample where it started is not an undoable action (LLFR-00140).

*Parent: HLFR-00099, HLFR-00085*

### LLFR-00862 Dragged delta marker point stays on its curve
While the user drags a point of a delta marker (LLFR-00433), the app must keep the point on the same curve.

*Parent: HLFR-00099, HLFR-00085*

### LLFR-00863 Other delta marker point stays in place
While the user drags a point of a delta marker (LLFR-00433), the app must keep the other point in place.

*Parent: HLFR-00099, HLFR-00085*

### LLFR-00864 Delta marker updated while dragging
While the user drags a point of a delta marker (LLFR-00433), the app must update the curly bracket and the value (LLFR-00169, LLFR-00171, LLFR-00261).

*Parent: HLFR-00099, HLFR-00085*

### LLFR-00434 Press on a delta marker point
A press that starts the drag of LLFR-00433 must not pin a data tip or pick a delta marker point.

*Parent: HLFR-00099, HLFR-00032*

### LLFR-00865 Drag keeps the first point
A press that starts the drag of LLFR-00433 must not change a first point already picked (LLFR-00163).

*Parent: HLFR-00099, HLFR-00032*

### LLFR-00866 Short press on a dot with a delta tool
While the Delta X or the Delta Y button is active, a press on a dot of a delta marker that moves the pointer less than 5 pixels must act as a click on the curve (LLFR-00163, LLFR-00680, LLFR-00164, LLFR-00681, LLFR-00682).

*Parent: HLFR-00099, HLFR-00032*

### LLFR-00867 Short press on a dot with no plot tool
While no plot tool is active, a press on a dot of a delta marker that moves the pointer less than 5 pixels must do nothing.

*Parent: HLFR-00099, HLFR-00032*

### LLFR-00868 No message on a short press on a dot
While no plot tool is active, a press on a dot of a delta marker that moves the pointer less than 5 pixels must not show any message.

*Parent: HLFR-00099, HLFR-00032*

### LLFR-00435 Dragging to a zero value
While the user drags a point of a delta marker (LLFR-00433), when the sample under the pointer would give a value of zero (LLFR-00431), the point must stay on the last sample that gave a value other than zero.

*Parent: HLFR-00099, HLFR-00098*

### LLFR-00436 Arrow label
The app must show the name of an arrow in a label next to the middle of its straight line, with its text parallel to the line as the line is shown on screen, in the arrow's color (LLFR-00373, LLFR-00788), on a label box as in LLFR-00704, on the side of the line of LLFR-00887.

*Parent: HLFR-00100*

### LLFR-00887 Side of the arrow label
The app must place the label of LLFR-00436 on the side of the line that is above the text as it is read (LLFR-00869), or on the other side only when no place along the line on that upper side keeps the whole label inside the plot's drawing area (LLFR-00437), except as in LLFR-00888.

*Parent: HLFR-00100*

### LLFR-00888 Arrow label with no room on either side
When no place along the line keeps the whole label of LLFR-00436 inside the plot's drawing area on either side of the line, the app must place the label on the side of the line that is above the text as it is read (LLFR-00869), next to the middle of the part of the line that is shown.

*Parent: HLFR-00100*

### LLFR-00869 Arrow label never upside down
The text of the label of LLFR-00436 must never be shown upside down, whatever the direction of the arrow.

*Parent: HLFR-00100*

### LLFR-00437 Arrow label follows the arrow
Whenever the position, angle or length of an arrow changes (LLFR-00376, LLFR-00377), or the plot's x-axis or y-axis range or size changes (LLFR-00374), the app must draw the label of LLFR-00436 again next to the middle of the part of the line that is shown, parallel to it, moved along the line by the shortest distance needed to keep the whole label inside the plot's drawing area, except as in LLFR-00871 and LLFR-00888.

*Parent: HLFR-00100, HLFR-00112*

### LLFR-00870 Arrow label follows the preview
While the user moves, rotates or stretches an arrow (LLFR-00376, LLFR-00377), the label of LLFR-00436 must follow the preview (LLFR-00779, LLFR-00782).

*Parent: HLFR-00112*

### LLFR-00871 Arrow label hidden
The label of LLFR-00436 must be hidden while no part of the arrow's line is shown.

*Parent: HLFR-00100, HLFR-00112*

### LLFR-00438 Default arrow name
The app must name each new arrow "Arrow N", where N is 1 for the first arrow drawn after the app starts and grows by 1 for each new arrow, in any plot.

*Parent: HLFR-00100*

### LLFR-00872 Arrow numbers not reused
The app must not reuse the number of a deleted arrow (LLFR-00438), even when the arrow's drawing is undone, while the app runs.

*Parent: HLFR-00100*

### LLFR-00439 Rename arrow action
When the user chooses "Rename" in the arrow menu (LLFR-00378), the app must let the user type a new name for that arrow.

*Parent: HLFR-00111*

### LLFR-00873 Renamed arrow label
After the user types a new arrow name (LLFR-00439), the app must show it in the arrow's label (LLFR-00436), except as in LLFR-00874.

*Parent: HLFR-00100, HLFR-00111*

### LLFR-00874 Empty arrow name
If the user enters an arrow name (LLFR-00439) that is empty or made only of spaces, the app must keep the previous name.

*Parent: HLFR-00111*

### LLFR-00875 No message on an empty arrow name
If the user enters an arrow name (LLFR-00439) that is empty or made only of spaces, the app must not show any message.

*Parent: HLFR-00111*

### LLFR-00876 Renaming keeps the arrow
Renaming an arrow (LLFR-00439) must not change the arrow's ends or color.

*Parent: HLFR-00111*
