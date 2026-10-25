"""Main window of plot_tool, holding the three panels (HLFR-00001)."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMainWindow, QSplitter, QVBoxLayout, QWidget

from view.plot_panel import PlotPanel
from view.signal_list_panel import SignalListPanel
from view.top_panel import TopPanel


class MainWindow(QMainWindow):
    """Top-level window that places the top, plot and signal list panels.

    Inputs: none.
    Attributes:
        top_panel: the TopPanel placed above the other two panels.
        plot_panel: the PlotPanel placed on the left, below the top panel.
        signal_list_panel: the SignalListPanel placed on the right of the
            plot panel.
    """

    WINDOW_TITLE_STR = "plot_tool"
    INITIAL_WIDTH_I = 1200
    INITIAL_HEIGHT_I = 800
    PLOT_PANEL_STRETCH_I = 4
    SIGNAL_LIST_STRETCH_I = 1

    def __init__(self) -> None:
        """Create the panels and arrange them in the window.

        Inputs: none.
        Outputs: none.
        """
        super().__init__()
        # LLFR-00058: the window holds the three panels of HLFR-00001.
        self.setWindowTitle(self.WINDOW_TITLE_STR)
        self.resize(self.INITIAL_WIDTH_I, self.INITIAL_HEIGHT_I)
        self.top_panel = TopPanel()
        self.plot_panel = PlotPanel()
        self.signal_list_panel = SignalListPanel()

        # LLFR-00058: the signal list panel is to the right of the plot
        # panel, and the user can drag the divider between them.
        self.lower_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.lower_splitter.addWidget(self.plot_panel)
        self.lower_splitter.addWidget(self.signal_list_panel)
        self.lower_splitter.setStretchFactor(0, self.PLOT_PANEL_STRETCH_I)
        self.lower_splitter.setStretchFactor(1, self.SIGNAL_LIST_STRETCH_I)

        # LLFR-00058: the top panel is above the other two panels.
        central_widget = QWidget()
        central_layout = QVBoxLayout(central_widget)
        central_layout.addWidget(self.top_panel)
        central_layout.addWidget(self.lower_splitter, 1)
        self.setCentralWidget(central_widget)
