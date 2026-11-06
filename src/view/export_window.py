"""The Export window: one button per export format (HLFR-00038).

The Export button and Ctrl+P (Cmd+P on macOS) open this window
(LLFR-00127, LLFR-01139). It shows three large buttons side by side,
each with an icon and a text, "PDF (all tabs)", "Word .docx (all tabs)"
and "PNG (one file per tab)" (LLFR-01229, LLFR-01263), and a "Cancel"
button below them (LLFR-01255). A click on a format closes the window
with that format chosen (LLFR-01256); Cancel, Esc and the close button
of the title bar close it with no format (LLFR-01257).

The button of the last format used is the default button, which the
Enter key clicks (LLFR-01258). That format is kept between launches in
the app's settings (QSettings), as one value for the Export button and
Ctrl+P of every window (LLFR-01259); ``remembered_export_format`` and
``remember_export_format`` read and write it. Tests isolate the settings
by setting ``settings_file_path_str`` to a file of their own (an INI
file), so they never read or change the settings of the user.
"""

from PyQt6.QtCore import QSettings, QSize, Qt
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QPushButton, QSizePolicy, QVBoxLayout)

from model.export_files import (
    DOCX_FORMAT_STR, EXPORT_FORMAT_TUPLE, PDF_FORMAT_STR, PNG_FORMAT_STR,
    cleaned_export_format)
from view import color_picker, icon_shapes, icons

# LLFR-00127: the title of the window.
EXPORT_WINDOW_TITLE_STR = "Export"
EXPORT_WINDOW_OBJECT_NAME_STR = "export_window"
# LLFR-01229: the text of each format button, from left to right.
FORMAT_TEXT_DICT = {
    PDF_FORMAT_STR: "PDF (all tabs)",
    DOCX_FORMAT_STR: "Word .docx (all tabs)",
    PNG_FORMAT_STR: "PNG (one file per tab)",
}
# LLFR-01263: the icon of each format button.
FORMAT_ICON_DICT = {
    PDF_FORMAT_STR: icon_shapes.PDF_FORMAT_ICON_STR,
    DOCX_FORMAT_STR: icon_shapes.DOCX_FORMAT_ICON_STR,
    PNG_FORMAT_STR: icon_shapes.PNG_FORMAT_ICON_STR,
}
# LLFR-01255: the text of the Cancel button.
CANCEL_TEXT_STR = "Cancel"
# LLFR-01229: large buttons: the size of their icon and their smallest
# size, in pixels.
FORMAT_ICON_SIZE_I = 40
FORMAT_BUTTON_MINIMUM_WIDTH_I = 190
FORMAT_BUTTON_MINIMUM_HEIGHT_I = 64
# LLFR-01229: the room around and between the buttons, in pixels.
WINDOW_MARGIN_I = 16
BUTTON_SPACING_I = 12
# LLFR-01259: the key of the last format in the settings.
EXPORT_FORMAT_KEY_STR = "export_format"
# LLFR-01259: an INI file used instead of the app's settings (tests);
# "" uses the settings of the app, the same as the recent colors.
settings_file_path_str = ""


def open_settings():
    """Open the settings that keep the last export format.

    Inputs: none.
    Outputs: a QSettings: the INI file of settings_file_path_str when it
        is set, or else the app's settings (the same as the recent
        colors, view.color_picker.open_settings).
    """
    # LLFR-01259: kept between launches in the app's settings.
    if settings_file_path_str:
        return QSettings(settings_file_path_str, QSettings.Format.IniFormat)
    return color_picker.open_settings()


def remembered_export_format() -> str:
    """Return the format whose button the Export window highlights.

    Inputs: none.
    Outputs: one of EXPORT_FORMAT_TUPLE: the last format the user
        clicked, or the PDF when none is remembered or the settings
        cannot be read.
    """
    # LLFR-01258, LLFR-01259: the last format, or the PDF.
    try:
        stored_value = open_settings().value(EXPORT_FORMAT_KEY_STR, "")
    except Exception:
        # LLFR-01259: settings that cannot be read remember nothing.
        stored_value = None
    return cleaned_export_format(stored_value)


def remember_export_format(format_str: str) -> None:
    """Keep the format the user clicked for the next Export window.

    Inputs:
        format_str: one of EXPORT_FORMAT_TUPLE; any other value is not
            kept.
    Outputs: none. A failure to write keeps the app running and only
        loses the change.
    """
    # LLFR-01259: one value, written to the settings at once.
    if format_str not in EXPORT_FORMAT_TUPLE:
        return
    try:
        settings = open_settings()
        settings.setValue(EXPORT_FORMAT_KEY_STR, format_str)
        settings.sync()
    except Exception:
        # LLFR-01259: a settings failure must not stop the export.
        return


class ExportWindow(QDialog):
    """The window in which the user chooses the export format.

    Inputs:
        parent: the window the Export window is shown over
            (LLFR-01262).
        default_format_str: the format whose button is the default
            button (LLFR-01258).
    Attributes:
        format_button_dict: format -> its QPushButton, in the order of
            EXPORT_FORMAT_TUPLE (LLFR-01229).
        cancel_button: the "Cancel" QPushButton (LLFR-01255).
        chosen_format_str: the format clicked, "" while none was.
    """

    def __init__(self, parent, default_format_str: str) -> None:
        """Build the window with its format buttons and Cancel button.

        Inputs:
            parent: the parent window.
            default_format_str: the highlighted format; an unknown value
                highlights the PDF.
        Outputs: none.
        """
        super().__init__(parent)
        # LLFR-00127: a separate window titled "Export".
        self.setObjectName(EXPORT_WINDOW_OBJECT_NAME_STR)
        self.setWindowTitle(EXPORT_WINDOW_TITLE_STR)
        self.setModal(True)
        self.chosen_format_str = ""
        column_layout = QVBoxLayout(self)
        column_layout.setContentsMargins(WINDOW_MARGIN_I, WINDOW_MARGIN_I,
                                         WINDOW_MARGIN_I, WINDOW_MARGIN_I)
        column_layout.setSpacing(BUTTON_SPACING_I)
        # LLFR-01229: three large buttons side by side, each with an
        # icon (LLFR-01263) and a text, from left to right.
        format_layout = QHBoxLayout()
        format_layout.setSpacing(BUTTON_SPACING_I)
        self.format_button_dict = {}
        for format_str in EXPORT_FORMAT_TUPLE:
            button = QPushButton(icons.icon_for(FORMAT_ICON_DICT[format_str]),
                                 FORMAT_TEXT_DICT[format_str])
            button.setIconSize(QSize(FORMAT_ICON_SIZE_I, FORMAT_ICON_SIZE_I))
            button.setMinimumSize(FORMAT_BUTTON_MINIMUM_WIDTH_I,
                                  FORMAT_BUTTON_MINIMUM_HEIGHT_I)
            button.setSizePolicy(QSizePolicy.Policy.Expanding,
                                 QSizePolicy.Policy.Fixed)
            # LLFR-01258: only the default button takes Enter.
            button.setAutoDefault(False)
            button.clicked.connect(
                lambda _checked=False, chosen_str=format_str:
                self.choose(chosen_str))
            format_layout.addWidget(button)
            self.format_button_dict[format_str] = button
        column_layout.addLayout(format_layout)
        # LLFR-01255: the Cancel button below the format buttons.
        cancel_layout = QHBoxLayout()
        cancel_layout.addStretch(1)
        self.cancel_button = QPushButton(CANCEL_TEXT_STR)
        self.cancel_button.setAutoDefault(False)
        # LLFR-01257: Cancel closes the window with no format.
        self.cancel_button.clicked.connect(self.reject)
        cancel_layout.addWidget(self.cancel_button)
        column_layout.addLayout(cancel_layout)
        self.set_default_format(default_format_str)

    def set_default_format(self, format_str: str) -> None:
        """Make one format button the default button.

        Inputs:
            format_str: the format; an unknown value gives the PDF.
        Outputs: none. The button also takes the keyboard focus, so the
            highlight shows and Enter or Space clicks it.
        """
        # LLFR-01258: the last format used, or the PDF.
        default_str = cleaned_export_format(format_str)
        for button_format_str, button in self.format_button_dict.items():
            button.setDefault(button_format_str == default_str)
        default_button = self.format_button_dict[default_str]
        default_button.setFocus(Qt.FocusReason.OtherFocusReason)

    def default_format(self) -> str:
        """Return the format of the default button.

        Inputs: none.
        Outputs: one of EXPORT_FORMAT_TUPLE, or "" when no button is the
            default button.
        """
        # LLFR-01258: the button that Enter clicks.
        for format_str, button in self.format_button_dict.items():
            if button.isDefault():
                return format_str
        return ""

    def choose(self, format_str: str) -> None:
        """Close the window with a format chosen.

        Inputs:
            format_str: the format of the clicked button.
        Outputs: none. The window is accepted.
        """
        # LLFR-01256: the click closes the window, and the caller runs
        # the export of that format.
        self.chosen_format_str = format_str
        self.accept()

    def reject(self) -> None:
        """Close the window with no format (Cancel, Esc, close button).

        Inputs: none.
        Outputs: none.
        """
        # LLFR-01257: nothing chosen, nothing saved.
        self.chosen_format_str = ""
        super().reject()
