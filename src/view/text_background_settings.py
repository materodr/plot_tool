"""The text background kept between launches (LLFR-01422).

The choice of "Transparent" or "Auto contrast" (HLFR-00167) is kept in
the app's settings (QSettings), the same settings as the recent colors
(view.color_picker.open_settings, LLFR-00419). Tests isolate the
settings by setting ``settings_file_path_str`` to a file of their own
(an INI file), so they never read or change the settings of the user.
"""

from PyQt6.QtCore import QSettings

from model.text_background import (
    TEXT_BACKGROUND_TUPLE, cleaned_text_background)
from view import color_picker

# LLFR-01422: the key of the choice in the settings.
TEXT_BACKGROUND_KEY_STR = "text_background"
# LLFR-01422: an INI file used instead of the app's settings (tests);
# "" uses the settings of the app.
settings_file_path_str = ""


def open_settings():
    """Open the settings that keep the text background.

    Inputs: none.
    Outputs: a QSettings: the INI file of settings_file_path_str when it
        is set, or else the app's settings.
    """
    # LLFR-01422: kept between launches in the app's settings.
    if settings_file_path_str:
        return QSettings(settings_file_path_str, QSettings.Format.IniFormat)
    return color_picker.open_settings()


def remembered_text_background() -> str:
    """Return the text background kept in the settings.

    Inputs: none.
    Outputs: one of TEXT_BACKGROUND_TUPLE; "Auto contrast" when the
        settings hold none, hold another value or cannot be read.
    """
    # LLFR-01421, LLFR-01422.
    try:
        stored_value = open_settings().value(TEXT_BACKGROUND_KEY_STR, None)
    except Exception:
        # LLFR-01421: settings that cannot be read give the default.
        stored_value = None
    return cleaned_text_background(stored_value)


def remember_text_background(choice_str: str) -> None:
    """Keep the text background for the next launches.

    Inputs:
        choice_str: one of TEXT_BACKGROUND_TUPLE; another value is not
            kept.
    Outputs: none. A failure to write keeps the app running and only
        loses the change.
    """
    # LLFR-01422, LLFR-01423: written each time the choice changes, by
    # the user, an undo or a redo.
    if choice_str not in TEXT_BACKGROUND_TUPLE:
        return
    try:
        settings = open_settings()
        settings.setValue(TEXT_BACKGROUND_KEY_STR, choice_str)
        settings.sync()
    except Exception:
        # LLFR-01422: a settings failure must not stop the app.
        return
