"""Plot panel: shows the plots where signal curves are drawn."""

from PyQt6.QtWidgets import QVBoxLayout, QWidget


class PlotPanel(QWidget):
    """Panel placed below the top panel, left of the signal list.

    Inputs: none.
    Attributes:
        panel_layout: vertical layout that holds the panel's content.
    """

    def __init__(self) -> None:
        """Create the empty panel.

        Inputs: none.
        Outputs: none.
        """
        super().__init__()
        # LLFR-00058: the plot panel exists and is placed by MainWindow.
        self.setObjectName("plot_panel")
        self.panel_layout = QVBoxLayout(self)
