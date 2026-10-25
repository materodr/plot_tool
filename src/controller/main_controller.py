"""Main controller: connects the view to the model (COR-00003)."""


class MainController:
    """Receives user actions from the view and updates model and view.

    The controller holds no Qt code, so it can be tested with a fake view
    (COR-00009).

    Inputs:
        main_window: the view object that holds the three panels.
    """

    def __init__(self, main_window: object) -> None:
        """Store the view.

        Inputs:
            main_window: the view object that holds the three panels.
        Outputs: none.
        """
        # LLFR-00058: the controller drives the main window and its panels.
        self.main_window = main_window

    def start(self) -> None:
        """Show the main window.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00058: show the window with its three panels.
        self.main_window.show()
