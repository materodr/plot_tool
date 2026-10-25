"""Top panel: holds the controls for opening a file and the plot tools."""

from PyQt6.QtWidgets import QHBoxLayout, QWidget


class TopPanel(QWidget):
    """Panel placed above the plot and signal list panels (HLFR-00001).

    Inputs: none.
    Attributes:
        button_layout: horizontal layout that holds the panel's buttons.
    """

    def __init__(self) -> None:
        """Create the empty panel with a horizontal layout for buttons.

        Inputs: none.
        Outputs: none.
        """
        super().__init__()
        # LLFR-00058: the top panel exists and is placed by MainWindow.
        self.setObjectName("top_panel")
        self.button_layout = QHBoxLayout(self)
        self.button_layout.addStretch(1)
