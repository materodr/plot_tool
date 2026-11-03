"""The shared color picker of the app and its recent colors (HLFR-00088).

Every "Color" option of the plots opens this one picker: the flag menu
(LLFR-00391), the area menu (LLFR-00351), the "Border color" and "Text
color" options of the text note menu (LLFR-00387) and, later, the arrow
menu (LLFR-00379). It wraps QColorDialog without its alpha channel, so
the user can choose any opaque color, with any red, green and blue value
from 0 to 255 (LLFR-00388).

Use:
    color_str = pick_color(parent_widget, current_color_str)
    # "#rrggbb" in lowercase, or None when the user cancelled.

The picker opens with the item's current color chosen (LLFR-00389). It
changes nothing by itself: the caller (through the controller) applies
the returned color as one undoable action, and does nothing for None or
for the color the item already has (LLFR-00390).

Every color option opens a submenu (LLFR-00388) built by
``add_color_submenu``: the recent colors (LLFR-00419), each with a
square swatch and its "#rrggbb" code, then "Other color...", which opens
the picker. The recent colors list is shared by every option and kept
between launches in the app's settings (QSettings); the rules of the
list are in model.recent_colors. A color goes first in the list each
time the user confirms it in the picker (``pick_color``) or chooses it
in the list (``remember_color``, called by the menu), even when it is
the item's current color. The colors the app gives by default and the
colors read from a layout file never pass through here, so they are
never added (LLFR-00419 Note). The item's current color is not marked
in the submenu: every entry looks the same.

Tests isolate the settings by setting ``settings_file_path_str`` to a
file of their own (an INI file), so they never read or change the
settings of the user.
"""

from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QColorDialog, QDialog

from model.recent_colors import (
    cleaned_recent_colors, recent_colors_after_use)
from view import theme

# LLFR-00388: the title of the picker window.
COLOR_PICKER_TITLE_STR = "Choose a color"
# LLFR-00388: the last option of every color submenu.
OTHER_COLOR_TEXT_STR = "Other color..."
# LLFR-00419: where the recent colors are kept between launches.
SETTINGS_ORGANIZATION_STR = "materodr"
SETTINGS_APPLICATION_STR = "plot_tool"
RECENT_COLORS_KEY_STR = "recent_colors"
# LLFR-00419: the size of the square swatch of an entry, in pixels, and
# the grey of its thin border, so that a white swatch stays visible.
SWATCH_SIZE_I = 14
SWATCH_BORDER_COLOR_STR = theme.MUTED_TEXT_COLOR_STR
# LLFR-00419: an INI file used instead of the user's settings (tests);
# "" uses the settings of the app.
settings_file_path_str = ""


def open_settings():
    """Open the settings that keep the recent colors.

    Inputs: none.
    Outputs: a QSettings: the app's settings, or the INI file of
        settings_file_path_str when it is set.
    """
    # LLFR-00419: kept between launches in the app's settings.
    if settings_file_path_str:
        return QSettings(settings_file_path_str, QSettings.Format.IniFormat)
    return QSettings(SETTINGS_ORGANIZATION_STR, SETTINGS_APPLICATION_STR)


def recent_color_list() -> list:
    """Return the recent colors, most recent first.

    Inputs: none.
    Outputs: a list of at most 8 lowercase "#rrggbb" colors; an empty
        list when the settings hold none or cannot be read.
    """
    # LLFR-00419: while the settings cannot be read, the list is empty.
    try:
        stored_value = open_settings().value(RECENT_COLORS_KEY_STR, [])
    except Exception:
        # LLFR-00419: any failure to read gives no recent color.
        return []
    return cleaned_recent_colors(stored_value)


def remember_color(color_str: str) -> None:
    """Put a confirmed or chosen color first in the recent colors.

    Inputs:
        color_str: the color, "#rrggbb"; it may be the color the item
            already has.
    Outputs: none. The list is written to the settings; a failure to
        write keeps the app running and only loses the change.
    """
    # LLFR-00419: first in the list, removed from any later place, at
    # most 8 colors, shared by every color option.
    color_list = recent_colors_after_use(recent_color_list(), color_str)
    try:
        settings = open_settings()
        settings.setValue(RECENT_COLORS_KEY_STR, color_list)
        settings.sync()
    except Exception:
        # LLFR-00419: a list that cannot be written never stops the app.
        return


def swatch_icon(color_str: str):
    """Return the small square swatch of a recent color.

    Inputs:
        color_str: the color, "#rrggbb".
    Outputs: a QIcon of a square filled with the color, with a thin grey
        border.
    """
    # LLFR-00419: a small square swatch filled with its color.
    pixmap = QPixmap(SWATCH_SIZE_I, SWATCH_SIZE_I)
    pixmap.fill(QColor(color_str))
    painter = QPainter(pixmap)
    painter.setPen(QColor(SWATCH_BORDER_COLOR_STR))
    painter.drawRect(0, 0, SWATCH_SIZE_I - 1, SWATCH_SIZE_I - 1)
    painter.end()
    return QIcon(pixmap)


def add_color_submenu(parent_menu, title_str: str, add_action):
    """Add the submenu of a color option to a menu.

    Inputs:
        parent_menu: the QMenu that gets the submenu.
        title_str: the option's text, for example "Color" or "Border
            color".
        add_action: function(target_menu, text_str, color_str) -> QAction
            that adds one entry to target_menu and makes it ask for
            color_str, a recent color, or "" for "Other color...".
    Outputs: the new QMenu: the recent colors, most recent first, each
        with its swatch and its "#rrggbb" code, then "Other color...".
        With no recent color, only "Other color...".
    """
    # LLFR-00388, LLFR-00419: the recent colors, then "Other color...".
    submenu = parent_menu.addMenu(title_str)
    for color_str in recent_color_list():
        action = add_action(submenu, color_str, color_str)
        action.setIcon(swatch_icon(color_str))
    add_action(submenu, OTHER_COLOR_TEXT_STR, "")
    return submenu


def build_color_dialog(parent, current_color_str: str,
                       title_str: str = COLOR_PICKER_TITLE_STR):
    """Build the color picker window, not shown yet.

    Inputs:
        parent: the parent widget of the window, or None.
        current_color_str: the item's current color, "#rrggbb"; an
            invalid value starts the picker at black.
        title_str: the window title.
    Outputs: a QColorDialog that starts at current_color_str and has no
        alpha channel, so every color it gives is opaque.
    """
    # LLFR-00388: one window for every item; no ShowAlphaChannel option,
    # so the colors are opaque, red, green and blue from 0 to 255.
    dialog = QColorDialog(parent)
    dialog.setWindowTitle(title_str)
    dialog.setOption(QColorDialog.ColorDialogOption.ShowAlphaChannel,
                     False)
    # LLFR-00389: the item's current color is shown as chosen.
    start_color = QColor(str(current_color_str))
    if not start_color.isValid():
        start_color = QColor(0, 0, 0)
    dialog.setCurrentColor(start_color)
    return dialog


def pick_color(parent, current_color_str: str,
               title_str: str = COLOR_PICKER_TITLE_STR):
    """Let the user choose a color in the shared color picker.

    Inputs:
        parent: the parent widget of the window, or None.
        current_color_str: the item's current color, "#rrggbb", shown as
            chosen when the picker opens (LLFR-00389).
        title_str: the window title.
    Outputs: the confirmed color as "#rrggbb" in lowercase, or None when
        the user cancelled the picker (LLFR-00390).
    """
    # LLFR-00388: the same picker window for every item.
    dialog = build_color_dialog(parent, current_color_str, title_str)
    try:
        accepted_b = dialog.exec() == QDialog.DialogCode.Accepted
        # LLFR-00390: cancel gives None; confirm gives the chosen color,
        # made opaque (LLFR-00388).
        chosen_color = dialog.currentColor()
    finally:
        dialog.deleteLater()
    if not accepted_b or not chosen_color.isValid():
        return None
    color_str = str(chosen_color.name(QColor.NameFormat.HexRgb)).lower()
    # LLFR-00419: a confirmed color goes first in the recent colors, even
    # when it is the item's current color.
    remember_color(color_str)
    return color_str
