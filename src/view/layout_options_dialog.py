"""The save options dialog of the Save layout button (LLFR-01212).

Before the save file dialog, the user chooses whether the layout file
holds the markers (pinned data tips, flags, areas and delta markers), all
the tabs or only the current tab, and the names of the open data files
(HLFR-00155). The dialog opens with the first values of LLFR-01213 each
time; Cancel ends the Save layout action (LLFR-01214).
"""

from PyQt6.QtWidgets import (
    QButtonGroup, QCheckBox, QDialog, QDialogButtonBox, QLabel, QRadioButton,
    QVBoxLayout)

# LLFR-01212: the texts of the dialog.
DIALOG_TITLE_STR = "Save layout"
INTRO_TEXT_STR = "Choose what the layout file holds:"
MARKERS_TEXT_STR = ("Include the markers (data tips, flags, areas and "
                    "delta markers)")
ALL_TABS_TEXT_STR = "All tabs"
CURRENT_TAB_TEXT_STR = "Only the current tab"
DATA_FILES_TEXT_STR = "Include the names of the open data files"
# LLFR-01212: the keys of the answer, as the layout controller reads it.
MARKERS_KEY_STR = "markers"
ALL_TABS_KEY_STR = "all_tabs"
DATA_FILES_KEY_STR = "data_files"


class LayoutOptionsDialog(QDialog):
    """The dialog of the three save options.

    Inputs:
        parent: the parent widget, the main window.
    Attributes:
        markers_box, data_files_box: the two check boxes.
        all_tabs_button, current_tab_button: the two choices of tabs.
    """

    def __init__(self, parent=None) -> None:
        """Create the dialog with the first values of LLFR-01213.

        Inputs:
            parent: the parent widget.
        Outputs: none.
        """
        super().__init__(parent)
        # LLFR-01212: the title and the three choices.
        self.setWindowTitle(DIALOG_TITLE_STR)
        dialog_layout = QVBoxLayout(self)
        dialog_layout.addWidget(QLabel(INTRO_TEXT_STR, self))
        # LLFR-01213: the markers on.
        self.markers_box = QCheckBox(MARKERS_TEXT_STR, self)
        self.markers_box.setChecked(True)
        dialog_layout.addWidget(self.markers_box)
        # LLFR-01213: "All tabs" chosen.
        self.all_tabs_button = QRadioButton(ALL_TABS_TEXT_STR, self)
        self.current_tab_button = QRadioButton(CURRENT_TAB_TEXT_STR, self)
        self.tab_group = QButtonGroup(self)
        self.tab_group.addButton(self.all_tabs_button)
        self.tab_group.addButton(self.current_tab_button)
        self.all_tabs_button.setChecked(True)
        dialog_layout.addWidget(self.all_tabs_button)
        dialog_layout.addWidget(self.current_tab_button)
        # LLFR-01213: the names of the data files off.
        self.data_files_box = QCheckBox(DATA_FILES_TEXT_STR, self)
        self.data_files_box.setChecked(False)
        dialog_layout.addWidget(self.data_files_box)
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel, self)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        dialog_layout.addWidget(button_box)

    def answer_dict(self) -> dict:
        """Return the choices shown in the dialog.

        Inputs: none.
        Outputs: {"markers": bool, "all_tabs": bool, "data_files": bool}.
        """
        # LLFR-01212: what the layout controller saves.
        return {MARKERS_KEY_STR: self.markers_box.isChecked(),
                ALL_TABS_KEY_STR: self.all_tabs_button.isChecked(),
                DATA_FILES_KEY_STR: self.data_files_box.isChecked()}
