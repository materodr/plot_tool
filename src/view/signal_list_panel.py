"""Signal list panel: shows the signals of the opened file."""

from PyQt6.QtWidgets import QVBoxLayout, QWidget


class SignalListPanel(QWidget):
    """Panel placed to the right of the plot panel (HLFR-00001).

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
        # LLFR-00058: the signal list panel exists and is placed by
        # MainWindow.
        self.setObjectName("signal_list_panel")
        self.panel_layout = QVBoxLayout(self)
