"""Main controller: connects the view to the model (COR-00003)."""

from controller.file_controller import FileController
from controller.plot_controller import PlotController


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

    def start(self) -> None:
        """Show the main window.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00058: show the window with its three panels.
        self.main_window.show()
