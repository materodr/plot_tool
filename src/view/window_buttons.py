"""Small icon buttons of the tabs and of the undocked windows.

The undock button sits on each docked tab of the main window
(LLFR-00977) and the dock button at the top-right corner of an undocked
window (LLFR-00990). Both show an icon of view.icon_shapes, the same on
every operating system (LLFR-00978, LLFR-00991), paler while disabled
(LLFR-00983), and a button tip with their name (LLFR-00979, LLFR-00992).
"""

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import QToolButton

from view import icon_shapes, icons

# LLFR-00992, LLFR-00979: the texts of the button tips.
DOCK_TIP_STR = "Dock"
UNDOCK_TIP_STR = "Undock"
# LLFR-00977: the size of the small undock button and its icon.
WINDOW_BUTTON_ICON_SIZE_I = 16
UNDOCK_BUTTON_SIZE_I = 20
UNDOCK_BUTTON_OBJECT_NAME_STR = "undock_button"


def build_window_icon_button(icon_name_str: str, tip_str: str,
                             object_name_str: str, parent=None):
    """Return a small flat button that shows a window icon.

    Inputs:
        icon_name_str: a name of icon_shapes.WINDOW_ICON_SHAPE_FUNCTION_DICT.
        tip_str: the text of its button tip.
        object_name_str: its objectName.
        parent: optional parent widget.
    Outputs: a QToolButton with the icon, paler while disabled
        (LLFR-00983), and its tip shown next to the pointer.
    """
    # LLFR-00978, LLFR-00991: the pictures; LLFR-00979, LLFR-00992: the
    # tips.
    button = QToolButton(parent)
    button.setObjectName(object_name_str)
    button.setIcon(icons.icon_for(icon_name_str))
    button.setIconSize(QSize(WINDOW_BUTTON_ICON_SIZE_I,
                             WINDOW_BUTTON_ICON_SIZE_I))
    button.setAutoRaise(True)
    button.setToolTip(tip_str)
    button.setAccessibleName(tip_str)
    # LLFR-00137: a click does not take the focus from the plots.
    button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    return button


def build_undock_button(parent=None):
    """Return the undock button shown on a docked tab.

    Inputs:
        parent: optional parent widget.
    Outputs: a small QToolButton with the undock icon and the tip
        "Undock".
    """
    # LLFR-00977, LLFR-00978, LLFR-00979.
    button = build_window_icon_button(
        icon_shapes.UNDOCK_ICON_STR, UNDOCK_TIP_STR,
        UNDOCK_BUTTON_OBJECT_NAME_STR, parent)
    button.setFixedSize(UNDOCK_BUTTON_SIZE_I, UNDOCK_BUTTON_SIZE_I)
    return button
