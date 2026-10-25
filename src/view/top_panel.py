"""Top panel: holds the controls for opening a file and the plot tools."""

from PyQt6.QtWidgets import QHBoxLayout, QWidget

from view.toggle_button import ToggleButton

OPEN_FILE_TEXT_STR = "Open file"
TIP_TEXT_STR = "Tip"


class TopPanel(QWidget):
    """Panel placed above the plot and signal list panels (HLFR-00001).

    Inputs: none.
    Attributes:
        button_layout: horizontal layout that holds the panel's buttons.
        open_file_button: the "Open file" ToggleButton (LLFR-00004).
        tip_button: the "Tip" ToggleButton (LLFR-00018).
    """

    def __init__(self) -> None:
        """Create the panel with its buttons, aligned to the left.

        Inputs: none.
        Outputs: none.
        """
        super().__init__()
        # LLFR-00058: the top panel exists and is placed by MainWindow.
        self.setObjectName("top_panel")
        self.button_layout = QHBoxLayout(self)
        # LLFR-00004: the "Open file" button; LLFR-00001: it shows when
        # it is active.
        self.open_file_button = ToggleButton(OPEN_FILE_TEXT_STR)
        self.open_file_button.setObjectName("open_file_button")
        # LLFR-00018: the "Tip" button.
        self.tip_button = ToggleButton(TIP_TEXT_STR)
        self.tip_button.setObjectName("tip_button")
        self.button_layout.addWidget(self.open_file_button)
        self.button_layout.addWidget(self.tip_button)
        # LLFR-00004, LLFR-00018: the stretch keeps the buttons on the
        # left.
        self.button_layout.addStretch(1)
