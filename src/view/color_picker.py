"""The shared color picker of the app (HLFR-00088).

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
"""

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QColorDialog, QDialog

# LLFR-00388: the title of the picker window.
COLOR_PICKER_TITLE_STR = "Choose a color"


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
    return str(chosen_color.name(QColor.NameFormat.HexRgb)).lower()
