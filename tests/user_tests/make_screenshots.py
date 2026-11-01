"""Save screenshots of the real main window in a representative state.

Run from the repository root (PyQt6 needed; offscreen works):

    python tests/user_tests/make_screenshots.py --output screenshots

It builds the real MainWindow and MainController, opens the good sample
CSV file and creates a state that shows most of the interface: two
tabs, three plots with several curves, a pinned tip, two vertical
markers, the grid, a search with results and an active plot tool. It
then saves PNG images of the whole window at 1400x900 and 1000x700, of
the window with a search that matches nothing, and of a message box.

CI runs it on every pull request and posts the images as PR comments
(see .github/workflows/tests.yml); fetch_screenshots.py downloads them.
The script makes images, it is not a test, so it is not named
``test_*.py`` and is not run by tests/build_test_matrix.py.
"""

import argparse
import os
import sys

USER_TESTS_FOLDER_STR = os.path.dirname(os.path.abspath(__file__))
REPOSITORY_ROOT_STR = os.path.dirname(os.path.dirname(USER_TESTS_FOLDER_STR))
SOURCE_FOLDER_STR = os.path.join(REPOSITORY_ROOT_STR, "src")
SAMPLE_FILE_PATH_STR = os.path.join(USER_TESTS_FOLDER_STR, "good",
                                    "signals_comma.csv")
LARGE_SIZE_TUPLE = (1400, 900)
SMALL_SIZE_TUPLE = (1000, 700)
# Signals of each plot of the first tab, from top to bottom.
FIRST_TAB_PLOT_LIST = [
    ["Sine_1Hz", "Cosine_1Hz", "Sine_3Hz"],
    ["Damped_sine", "Square_0p5Hz"],
    ["Temperature"],
]
SECOND_TAB_PLOT_LIST = [["Pressure"], ["Noise", "Ramp"]]
FIRST_TAB_NAME_STR = "Oscillations"
SECOND_TAB_NAME_STR = "Environment"
SEARCH_TEXT_STR = "sine"
NO_MATCH_SEARCH_TEXT_STR = "voltage"
# Time (s) and signal of the pinned tip, on the first plot.
PINNED_TIP_SIGNAL_STR = "Sine_1Hz"
PINNED_TIP_TIME_S = 2.25
# Times (s) of the two vertical markers, on the first plot.
MARKER_TIME_TUPLE = (4.5, 8.0)


def process_events(application, repeat_count_i: int = 5) -> None:
    """Let Qt and matplotlib finish layouts and pending draws.

    Inputs:
        application: the QApplication.
        repeat_count_i: how many times the events are processed.
    Outputs: none.
    """
    for _ in range(repeat_count_i):
        application.processEvents()


def draw_all_plots(main_window, application) -> None:
    """Draw every plot canvas now, so the grab shows final pixels.

    Inputs:
        main_window: the MainWindow.
        application: the QApplication.
    Outputs: none.
    """
    process_events(application)
    for plot_widget in main_window.plot_panel.plot_widget_dict.values():
        plot_widget.update_legend()
        plot_widget.canvas.draw()
    process_events(application)


def add_plots(controller, main_window, plot_signal_list: list) -> list:
    """Create plots in the current tab and draw the given signals.

    Inputs:
        controller: the MainController.
        main_window: the MainWindow.
        plot_signal_list: one list of signal names per plot.
    Outputs: the ids of the new plots, from top to bottom.
    """
    plot_controller = controller.plot_controller
    plot_id_list = []
    for signal_name_list in plot_signal_list:
        plot_controller.on_signal_double_clicked(signal_name_list[0])
        plot_id_i = main_window.plot_panel.plot_id_list(
            main_window.current_tab_id())[-1]
        for signal_name_str in signal_name_list[1:]:
            plot_controller.on_signal_dropped(plot_id_i, signal_name_str)
        plot_id_list.append(plot_id_i)
    return plot_id_list


def build_window(size_tuple: tuple):
    """Build the window and controller in the representative state.

    Inputs:
        size_tuple: (width, height) of the window in pixels.
    Outputs: a tuple (main_window, controller).
    """
    import math
    from unittest import mock

    from PyQt6.QtWidgets import QFileDialog

    from controller.main_controller import MainController
    from view.main_window import MainWindow

    main_window = MainWindow()
    main_window.resize(*size_tuple)
    controller = MainController(main_window)
    controller.start()
    with mock.patch.object(QFileDialog, "getOpenFileName",
                           return_value=(SAMPLE_FILE_PATH_STR, "")):
        controller.file_controller.open_file_requested()
    plot_controller = controller.plot_controller
    first_tab_id_i = main_window.current_tab_id()
    plot_controller.on_rename_tab(first_tab_id_i, FIRST_TAB_NAME_STR)
    # The second tab is filled first, so the first one is shown at the
    # end with its plots.
    plot_controller.on_add_tab()
    plot_controller.on_rename_tab(main_window.current_tab_id(),
                                  SECOND_TAB_NAME_STR)
    add_plots(controller, main_window, SECOND_TAB_PLOT_LIST)
    main_window.set_current_tab(first_tab_id_i)
    plot_id_list = add_plots(controller, main_window, FIRST_TAB_PLOT_LIST)
    first_plot_id_i = plot_id_list[0]
    plot_controller.on_tip_pin(
        first_plot_id_i, PINNED_TIP_SIGNAL_STR, PINNED_TIP_TIME_S,
        math.sin(2.0 * math.pi * PINNED_TIP_TIME_S))
    # Markers are placed only while the Vertical marker tool is active.
    main_window.top_panel.marker_button.click()
    for marker_time_s in MARKER_TIME_TUPLE:
        plot_controller.on_marker_place(first_plot_id_i, marker_time_s)
    # The Grid and Tip buttons are clicked like a user would; Tip ends
    # the Vertical marker tool.
    main_window.top_panel.grid_button.click()
    main_window.top_panel.tip_button.click()
    main_window.signal_list_panel.search_box.setText(SEARCH_TEXT_STR)
    return main_window, controller


def save_window(main_window, application, path_str: str) -> None:
    """Draw everything and save a PNG of the whole window.

    Inputs:
        main_window: the MainWindow.
        application: the QApplication.
        path_str: the PNG file to write.
    Outputs: none.
    """
    draw_all_plots(main_window, application)
    if not main_window.grab().save(path_str, "PNG"):
        raise RuntimeError(f"could not save {path_str}")
    print(f"saved {path_str}")


def save_message_box(main_window, application, path_str: str) -> None:
    """Save a PNG of the Full Tab Notification box.

    Inputs:
        main_window: the parent MainWindow.
        application: the QApplication.
        path_str: the PNG file to write.
    Outputs: none.
    """
    from view import message_boxes
    box = message_boxes.build_full_tab_box(main_window)
    box.show()
    process_events(application)
    if not box.grab().save(path_str, "PNG"):
        raise RuntimeError(f"could not save {path_str}")
    box.close()
    box.deleteLater()
    print(f"saved {path_str}")


def main() -> int:
    """Build the window states and save the screenshots.

    Inputs: none (command-line arguments: --output folder).
    Outputs: the exit code, 0 when every image was saved.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", default="screenshots",
                        help="folder where the PNG files are written")
    argument_namespace = parser.parse_args()
    os.makedirs(argument_namespace.output, exist_ok=True)
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    if SOURCE_FOLDER_STR not in sys.path:
        sys.path.insert(0, SOURCE_FOLDER_STR)
    from PyQt6.QtWidgets import QApplication
    application = QApplication.instance() or QApplication(sys.argv)

    def output_path(name_str: str) -> str:
        """Return the path of a PNG in the output folder.

        Inputs:
            name_str: the image name, without extension.
        Outputs: the file path.
        """
        return os.path.join(argument_namespace.output, name_str + ".png")

    for name_str, size_tuple in (("window_1400x900", LARGE_SIZE_TUPLE),
                                 ("window_1000x700", SMALL_SIZE_TUPLE)):
        main_window, controller = build_window(size_tuple)
        save_window(main_window, application, output_path(name_str))
        if size_tuple == SMALL_SIZE_TUPLE:
            # The same window with a search that matches nothing.
            main_window.signal_list_panel.search_box.setText(
                NO_MATCH_SEARCH_TEXT_STR)
            save_window(main_window, application,
                        output_path("no_match_1000x700"))
            save_message_box(main_window, application,
                             output_path("full_tab_box"))
        main_window.close()
        main_window.deleteLater()
        process_events(application)
    return 0


if __name__ == "__main__":
    sys.exit(main())
