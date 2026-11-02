"""File dialogs that are built once and shown quickly (HLFR-00091).

LLFR-00406 asks every file dialog to appear within 0.65 s of the
click, the first click after the start included. The app keeps the
system's own (native) file dialogs. It builds each QFileDialog once,
after the main window is shown, and shows the same object again on
every later click, so no click pays for building and styling the
dialog.

No dialog is ever shown without a click (issue #165). Issue #154 made
macOS load its open and save panels by showing and closing one of each
right after the start; the owner saw them flash, and that work, run
while the splash screen still waited for the window, blocked the app
for about 0.9 s. The preparation now only builds the dialogs, and on
macOS creates one system open panel and one save panel without showing
them (warm_up_system_panel), so that the system loads the panel code
before the first click. Measured on the macOS build check: the first
Open file dialog of a launch took 0.91 to 1.04 s without this, 0.41 to
0.48 s with it; every later dialog takes 0.4 to 0.5 s either way,
because the system builds a new panel each time Qt shows one.

The preparation runs in small steps, one per turn of the event loop,
starting PREPARE_START_DELAY_MS_I after the window is shown
(schedule_preparation), so that the window answers the user between
the steps (LLFR-00188).

A FileDialogPool keeps these dialogs:

- ``register(key_str, build_function)`` names a dialog and the factory
  function that builds it (a function of no arguments returning a
  QFileDialog, for example ``MainWindow.build_layout_save_dialog``);
- ``prepare_all()`` runs every preparation step at once;
- ``schedule_preparation(parent)`` runs them one per event-loop turn;
- ``prepared_dialog(key_str, start_folder_str)`` returns the dialog of a
  key, built on first use when it was not prepared, reset for a new
  use: it shows the given folder (LLFR-00204, LLFR-00220), its first
  name filter and, in Qt's own dialog (used where the system has none),
  no file name left from an earlier use;
- ``run_file_dialog(dialog)`` shows a dialog modally and returns the
  chosen path ("" when cancelled).

Any other file dialog is made fast the same way: register its factory
function with a new key and ask for it with prepared_dialog, as the
Save signals dialog does.
"""

import ctypes
import ctypes.util
import sys
import time

from PyQt6 import sip
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QDialog, QLineEdit

# LLFR-00406: the name of the field where a file name is typed in Qt's
# own file dialog (used where the system has no file dialog, as in the
# tests).
FILE_NAME_FIELD_NAME_STR = "fileNameEdit"
# LLFR-00406: the platform whose system file panels are slow on their
# first use in a process.
MACOS_PLATFORM_STR = "darwin"
# LLFR-00406, LLFR-00188: the preparation starts this long after the
# window is shown, so that the window is drawn and answers first.
PREPARE_START_DELAY_MS_I = 250
# LLFR-00406: the Objective-C runtime library and the panel classes
# and class methods that create a system panel without showing it.
OBJECTIVE_C_LIBRARY_STR = "objc"
OBJECTIVE_C_LIBRARY_PATH_STR = "/usr/lib/libobjc.A.dylib"
SYSTEM_PANEL_TUPLE = ((b"NSOpenPanel", b"openPanel"),
                      (b"NSSavePanel", b"savePanel"))
# LLFR-00406: the panels created by warm_up_system_panel, kept for the
# whole run so that the system keeps what it loaded for them.
KEPT_PANEL_LIST = []


def objective_c_runtime() -> tuple:
    """Load the Objective-C runtime of macOS through ctypes.

    Inputs: none.
    Outputs: a tuple (the runtime library, its objc_msgSend function
        set up for messages without arguments).
    """
    # LLFR-00406: ctypes is part of Python, so no library is added
    # (COR-00011).
    library_path_str = (ctypes.util.find_library(OBJECTIVE_C_LIBRARY_STR)
                        or OBJECTIVE_C_LIBRARY_PATH_STR)
    runtime = ctypes.CDLL(library_path_str)
    runtime.objc_getClass.restype = ctypes.c_void_p
    runtime.objc_getClass.argtypes = [ctypes.c_char_p]
    runtime.sel_registerName.restype = ctypes.c_void_p
    runtime.sel_registerName.argtypes = [ctypes.c_char_p]
    send_message = runtime.objc_msgSend
    send_message.restype = ctypes.c_void_p
    send_message.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    return runtime, send_message


def warm_up_system_panel(panel_tuple: tuple,
                         platform_str: str = sys.platform) -> str:
    """Make macOS load one kind of system panel without showing it.

    Inputs:
        panel_tuple: (class name, class method) as bytes, one entry of
            SYSTEM_PANEL_TUPLE.
        platform_str: the platform name, as sys.platform.
    Outputs: "warmed" when the panel was created, "skipped" on other
        systems, "failed" when the system could not be asked. Nothing is
        shown on screen.
    """
    # LLFR-00406: [NSOpenPanel openPanel] and [NSSavePanel savePanel]
    # create the panel as the first dialog of a process would, so the
    # system loads its code; only ordering a panel front shows it, and
    # that is never done here (issue #165).
    if platform_str != MACOS_PLATFORM_STR:
        return "skipped"
    class_name_bytes, method_name_bytes = panel_tuple
    try:
        runtime, send_message = objective_c_runtime()
        # LLFR-00406: the runtime answers with object addresses.
        panel_class_i = runtime.objc_getClass(class_name_bytes)
        if not panel_class_i:
            return "failed"
        panel_i = send_message(panel_class_i,
                               runtime.sel_registerName(method_name_bytes))
        if not panel_i:
            return "failed"
        # LLFR-00406: kept, so it is not freed at the end of the
        # event-loop turn.
        KEPT_PANEL_LIST.append(send_message(
            panel_i, runtime.sel_registerName(b"retain")))
        # LLFR-00406: TEMPORARY experiment (issue #165), removed before
        # review: draw the panel off screen, without ordering it front.
        import os
        if os.environ.get("PLOT_TOOL_PANEL_DISPLAY_EXPERIMENT") == "1":
            send_message(panel_i, runtime.sel_registerName(b"display"))
    except (OSError, AttributeError, ValueError):
        return "failed"
    return "warmed"


def run_file_dialog(dialog) -> str:
    """Show a file dialog modally and return the chosen path.

    Inputs:
        dialog: a QFileDialog.
    Outputs: the first selected path, or "" when the user cancelled
        (LLFR-00007, LLFR-00130, LLFR-00222).
    """
    # LLFR-00005, LLFR-00128, LLFR-00219, LLFR-00221: the modal dialog.
    if dialog.exec() != QDialog.DialogCode.Accepted.value:
        return ""
    selected_file_list = dialog.selectedFiles()
    if not selected_file_list:
        return ""
    return str(selected_file_list[0])


def reset_for_new_use(dialog, start_folder_str: str) -> None:
    """Make a dialog shown before look as a newly built one.

    Inputs:
        dialog: a QFileDialog.
        start_folder_str: the folder to show; "" keeps the folder the
            dialog shows now (the folder Qt chose when it was built, or
            the one it showed last).
    Outputs: none. The first name filter is chosen and the typed file
        name of an earlier use is cleared.
    """
    # LLFR-00204, LLFR-00220: the folder chosen by the controllers.
    if start_folder_str:
        dialog.setDirectory(start_folder_str)
    # LLFR-00128, LLFR-00219, LLFR-00221: the filters are kept as they
    # were built; the first one is chosen, as in a new dialog.
    name_filter_list = dialog.nameFilters()
    if name_filter_list:
        dialog.selectNameFilter(name_filter_list[0])
    # LLFR-00219, LLFR-00406: a name typed before a cancel is not kept.
    file_name_field = dialog.findChild(QLineEdit, FILE_NAME_FIELD_NAME_STR)
    if file_name_field is not None:
        file_name_field.clear()


class FileDialogPool:
    """The app's file dialogs, each built once and reused (LLFR-00406).

    Inputs:
        platform_str: the platform name (sys.platform by default); on
            macOS the preparation also warms up the system's panels.
        warm_up_function: function taking an entry of
            SYSTEM_PANEL_TUPLE and the platform name, that warms up that
            system panel without showing it; warm_up_system_panel by
            default.
    Attributes:
        build_function_dict: key -> factory function of the dialog.
        dialog_dict: key -> the QFileDialog built for it.
        prepared_b: True once every preparation step has run.
        prepare_duration_s: seconds spent in the preparation steps.
        longest_step_s: seconds of the longest preparation step.
        step_count_i: how many preparation steps have run.
        step_duration_list: the seconds of each step that has run.
        panel_state_list: what each panel warm-up step did, as
            warm_up_system_panel returns.
        step_timer: the QTimer of schedule_preparation, or None.
    """

    def __init__(self, platform_str: str = sys.platform,
                 warm_up_function=warm_up_system_panel) -> None:
        """Create an empty pool.

        Inputs:
            platform_str: the platform name, as sys.platform.
            warm_up_function: see the class docstring.
        Outputs: none.
        """
        # LLFR-00406: no dialog is built before the preparation or the
        # first use.
        self.platform_str = str(platform_str)
        self.warm_up_function = warm_up_function
        self.build_function_dict = {}
        self.dialog_dict = {}
        self.prepared_b = False
        self.prepare_duration_s = 0.0
        self.longest_step_s = 0.0
        self.step_count_i = 0
        self.step_duration_list = []
        self.panel_state_list = []
        self.pending_step_list = []
        self.step_timer = None

    def register(self, key_str: str, build_function) -> None:
        """Name a dialog and the function that builds it.

        Inputs:
            key_str: the name of the dialog, for example "open_file".
            build_function: function without arguments that returns a
                new QFileDialog, not shown.
        Outputs: none.
        """
        # LLFR-00406: every file dialog of the app is kept here.
        self.build_function_dict[str(key_str)] = build_function

    def key_list(self) -> list:
        """Return the names of the registered dialogs.

        Inputs: none.
        Outputs: a list of str, in the order they were registered.
        """
        # LLFR-00406: the dialogs prepared after the window is shown.
        return list(self.build_function_dict)

    def is_built(self, key_str: str) -> bool:
        """Tell whether the dialog of a key exists.

        Inputs:
            key_str: a registered name.
        Outputs: True when its QFileDialog was built and not deleted.
        """
        # LLFR-00406: a dialog deleted with its parent is built again.
        dialog = self.dialog_dict.get(key_str)
        return dialog is not None and not sip.isdeleted(dialog)

    def dialog(self, key_str: str):
        """Return the dialog of a key, building it on first use.

        Inputs:
            key_str: a registered name.
        Outputs: the QFileDialog; the same object on every call.
        """
        # LLFR-00406: built once, then shown again on every click.
        if not self.is_built(key_str):
            self.dialog_dict[key_str] = self.build_function_dict[key_str]()
        return self.dialog_dict[key_str]

    def prepared_dialog(self, key_str: str, start_folder_str: str = ""):
        """Return the dialog of a key, ready to be shown.

        Inputs:
            key_str: a registered name.
            start_folder_str: the folder the dialog must show; "" keeps
                its current folder.
        Outputs: the QFileDialog, reset as by reset_for_new_use.
        """
        # LLFR-00406, LLFR-00204, LLFR-00220: the same dialog, in the
        # folder the controller chose.
        dialog = self.dialog(key_str)
        reset_for_new_use(dialog, start_folder_str)
        return dialog

    def build_and_polish(self, key_str: str) -> None:
        """Build the dialog of a key, if needed, and style it.

        Inputs:
            key_str: a registered name.
        Outputs: none. The dialog is not shown.
        """
        # LLFR-00406: one preparation step; nothing appears on screen.
        self.dialog(key_str).ensurePolished()

    def warm_up_panel(self, panel_tuple: tuple) -> None:
        """Warm up one kind of system panel, without showing anything.

        Inputs:
            panel_tuple: an entry of SYSTEM_PANEL_TUPLE.
        Outputs: none. panel_state_list tells what was done.
        """
        # LLFR-00406: on macOS only (warm_up_system_panel).
        self.panel_state_list.append(
            self.warm_up_function(panel_tuple, self.platform_str))

    def panel_state_str(self) -> str:
        """Describe what the panel warm-up did.

        Inputs: none.
        Outputs: the states of panel_state_list joined by commas, or
            "none" when no warm-up step has run.
        """
        # LLFR-00406: reported by the startup probe.
        return ",".join(self.panel_state_list) or "none"

    def preparation_step_list(self) -> list:
        """Return the preparation steps, in the order they run.

        Inputs: none.
        Outputs: a list of functions without arguments: on macOS one
            warm-up step per kind of system panel first, then one step
            per registered dialog.
        """
        # LLFR-00406: the panel warm-up first, because the first panel
        # of a process is the slowest one to show; one kind per step,
        # so that each step blocks the window for a shorter time.
        step_list = []
        if self.platform_str == MACOS_PLATFORM_STR:
            for panel_tuple in SYSTEM_PANEL_TUPLE:
                step_list.append(lambda panel_tuple=panel_tuple:
                                 self.warm_up_panel(panel_tuple))
        for key_str in self.key_list():
            step_list.append(
                lambda key_str=key_str: self.build_and_polish(key_str))
        return step_list

    def run_step(self, step) -> None:
        """Run one preparation step and time it.

        Inputs:
            step: a function of preparation_step_list.
        Outputs: none.
        """
        # LLFR-00406, LLFR-00188: the steps are timed, to check that
        # none blocks the window for long.
        start_s = time.perf_counter()
        step()
        step_s = time.perf_counter() - start_s
        self.prepare_duration_s += step_s
        self.longest_step_s = max(self.longest_step_s, step_s)
        self.step_duration_list.append(step_s)
        self.step_count_i += 1

    def prepare_all(self) -> None:
        """Run every preparation step at once.

        Inputs: none.
        Outputs: none. Every registered dialog is built and styled.
        """
        # LLFR-00406: as schedule_preparation, without waiting.
        if self.step_timer is not None:
            self.step_timer.stop()
        for step in self.preparation_step_list():
            self.run_step(step)
        self.pending_step_list = []
        self.prepared_b = True

    def schedule_preparation(self, parent,
                             start_delay_ms_i: int = PREPARE_START_DELAY_MS_I
                             ) -> None:
        """Run the preparation steps later, one per event-loop turn.

        Inputs:
            parent: the QObject that owns the timer (the main window),
                so that no step runs once it is deleted.
            start_delay_ms_i: milliseconds before the first step.
        Outputs: none. prepared_b becomes True after the last step.
        """
        # LLFR-00406, LLFR-00188: after the window is shown, and with
        # the event loop running between the steps, so that a click is
        # answered at once and the window is never blocked for long.
        self.pending_step_list = self.preparation_step_list()
        self.step_timer = QTimer(parent)
        self.step_timer.setSingleShot(True)
        self.step_timer.timeout.connect(self.run_next_step)
        self.step_timer.start(max(0, int(start_delay_ms_i)))

    def run_next_step(self) -> None:
        """Run the next scheduled preparation step.

        Inputs: none.
        Outputs: none. The next step is scheduled for the next turn of
            the event loop, or prepared_b is set after the last one.
        """
        # LLFR-00406: one step per turn.
        if self.pending_step_list:
            self.run_step(self.pending_step_list.pop(0))
        if self.pending_step_list:
            self.step_timer.start(0)
        else:
            self.prepared_b = True
