"""Main controller: connects the view to the model (COR-00003)."""

from controller.export_controller import ExportController
from controller.file_controller import FileController
from controller.plot_controller import PlotController
from controller.signal_list_controller import SignalListController


class MainController:
    """Receives user actions from the view and updates model and view.

    The controller holds no Qt code, so it can be tested with a fake view
    (COR-00009).

    Inputs:
        main_window: the view object that holds the three panels and
            offers the facade methods used by the controllers.
    Attributes:
        main_window: the view.
        file_controller: the FileController of the open-file flow.
        plot_controller: the PlotController of the tabs and plots.
        signal_list_controller: the SignalListController of the search.
        export_controller: the ExportController of the Export menu and
            the Copy button.
    """

    def __init__(self, main_window: object) -> None:
        """Store the view and connect the controllers to it.

        Inputs:
            main_window: the view object that holds the three panels.
        Outputs: none.
        """
        # LLFR-00058: the controller drives the main window and its panels.
        self.main_window = main_window
        # LLFR-00005: the Open file button starts the open-file flow.
        self.file_controller = FileController(main_window)
        main_window.set_open_file_handler(
            self.file_controller.open_file_requested)
        # LLFR-00015, LLFR-00019, LLFR-00026, LLFR-00042: the plot
        # controller listens to opened files and to the plot panel.
        self.plot_controller = PlotController(main_window,
                                              self.file_controller)
        # LLFR-00095, LLFR-00104: the search box filters the signal
        # list; registered after the plot controller, so it runs after
        # the FileController has shown all names of a new file.
        self.signal_list_controller = SignalListController(
            main_window, self.file_controller)
        # LLFR-00128, LLFR-00133: the Export menu and the Copy button
        # run the export controller's flows.
        self.export_controller = ExportController(main_window)
        main_window.set_export_handlers(
            self.export_controller.on_export_requested,
            self.export_controller.on_copy_requested)

    def start(self) -> None:
        """Show the main window.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00058: show the window with its three panels.
        self.main_window.show()
