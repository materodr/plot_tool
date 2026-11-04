"""Small icon buttons of the tabs and of the undocked windows.

The undock button sits inside each docked tab of the main window that
can be undocked (LLFR-01012, LLFR-01018), and the dock button inside
each tab of an undocked window (LLFR-01025). Both show an icon of
view.icon_shapes, the same on every operating system (LLFR-01013,
LLFR-01026), and a button tip with their name (LLFR-01014, LLFR-01027).

They are drawn flat, as part of their tab: no border or background of
their own, the icon in the color of the tab's text (LLFR-01147), and a
pale rounded highlight behind the icon while the pointer is over them,
like the close button of a browser tab (LLFR-01148). The QToolButton
sits in a holder widget whose margins keep it inside the tab, clear of
the tab's borders (LLFR-01154); the tab bar makes the tab wide enough
for its name and the holder side by side (LLFR-01155).
"""

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import QHBoxLayout, QToolButton, QWidget

from view import icon_shapes, icons, theme

# LLFR-01027, LLFR-01014: the texts of the button tips.
DOCK_TIP_STR = "Dock"
UNDOCK_TIP_STR = "Undock"
# LLFR-01012, LLFR-01025: the size of the small tab buttons and their
# icon.
WINDOW_BUTTON_ICON_SIZE_I = 16
TAB_ICON_SIZE_I = 14
TAB_BUTTON_SIZE_I = 18
UNDOCK_BUTTON_SIZE_I = TAB_BUTTON_SIZE_I
UNDOCK_BUTTON_OBJECT_NAME_STR = "undock_button"
DOCK_BUTTON_OBJECT_NAME_STR = "dock_button"
TAB_BUTTON_HOLDER_OBJECT_NAME_STR = "tab_button_holder"
# LLFR-01154: the room between the button and the tab's borders: on the
# left, the gap after the name; on the right, the tab's right margin and
# border (theme.tab_style_sheet) plus the padding; above and below.
TAB_BUTTON_LEFT_GAP_I = 4
TAB_BUTTON_RIGHT_GAP_I = (theme.TAB_SPACING_I + theme.TAB_BORDER_WIDTH_I
                          + 4)
TAB_BUTTON_VERTICAL_GAP_I = 2
# LLFR-01148: the corner radius of the hover highlight.
TAB_BUTTON_RADIUS_I = 4


def build_window_icon_button(icon_name_str: str, tip_str: str,
                             object_name_str: str, parent=None):
    """Return a small flat button that shows a window icon.

    Inputs:
        icon_name_str: a name of icon_shapes.WINDOW_ICON_SHAPE_FUNCTION_DICT.
        tip_str: the text of its button tip.
        object_name_str: its objectName.
        parent: optional parent widget.
    Outputs: a QToolButton with the icon and its tip shown next to the
        pointer.
    """
    # LLFR-01013, LLFR-01026: the pictures; LLFR-01014, LLFR-01027: the
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


def tab_button_style_sheet(object_name_str: str) -> str:
    """Return the style sheet of a flat tab button.

    Inputs:
        object_name_str: the objectName of the QToolButton.
    Outputs: a style sheet with no border and no background, and a pale
        rounded highlight on hover (LLFR-01147, LLFR-01148).
    """
    # LLFR-01147: drawn as part of the tab; LLFR-01148: the highlight.
    selector_str = f"QToolButton#{object_name_str}"
    return (f"{selector_str} {{ border: none; padding: 0px; margin: 0px; "
            f"background: transparent; "
            f"border-radius: {TAB_BUTTON_RADIUS_I}px; }}\n"
            f"{selector_str}:hover {{ background: "
            f"{theme.TAB_BUTTON_HOVER_COLOR_STR}; }}\n"
            f"{selector_str}:pressed {{ background: "
            f"{theme.TAB_BUTTON_PRESSED_COLOR_STR}; }}\n")


class TabIconButton(QWidget):
    """The undock or dock button of a tab, in its holder.

    Inputs:
        icon_name_str: icon_shapes.UNDOCK_ICON_STR or DOCK_ICON_STR.
        tip_str: UNDOCK_TIP_STR or DOCK_TIP_STR.
        object_name_str: the objectName of the QToolButton.
        parent: optional parent widget.
    Attributes:
        button: the flat QToolButton; its clicked signal is the click of
            the tab button.
        icon_name_str: the icon it shows.
        selected_b: True while its tab is the selected one.
    """

    def __init__(self, icon_name_str: str, tip_str: str,
                 object_name_str: str, parent=None) -> None:
        """Create the holder and its flat button.

        Inputs: see the class docstring.
        Outputs: none.
        """
        super().__init__(parent)
        self.setObjectName(TAB_BUTTON_HOLDER_OBJECT_NAME_STR)
        self.icon_name_str = icon_name_str
        self.selected_b = False
        # LLFR-01154: the margins keep the button clear of the borders.
        layout = QHBoxLayout(self)
        layout.setContentsMargins(TAB_BUTTON_LEFT_GAP_I,
                                  TAB_BUTTON_VERTICAL_GAP_I,
                                  TAB_BUTTON_RIGHT_GAP_I,
                                  TAB_BUTTON_VERTICAL_GAP_I)
        layout.setSpacing(0)
        self.button = build_window_icon_button(icon_name_str, tip_str,
                                               object_name_str, self)
        self.button.setIconSize(QSize(TAB_ICON_SIZE_I, TAB_ICON_SIZE_I))
        self.button.setFixedSize(TAB_BUTTON_SIZE_I, TAB_BUTTON_SIZE_I)
        # LLFR-01147, LLFR-01148: flat, with the hover highlight.
        self.button.setStyleSheet(tab_button_style_sheet(object_name_str))
        layout.addWidget(self.button)
        self.setFixedSize(
            TAB_BUTTON_LEFT_GAP_I + TAB_BUTTON_SIZE_I
            + TAB_BUTTON_RIGHT_GAP_I,
            TAB_BUTTON_SIZE_I + 2 * TAB_BUTTON_VERTICAL_GAP_I)
        self.set_selected_look(False)

    def icon_color_str(self) -> str:
        """Return the color the icon is drawn in.

        Inputs: none.
        Outputs: the text color of the selected tab, or of the
            unselected tabs (LLFR-01147).
        """
        # LLFR-01147: the color of the tab's text.
        if self.selected_b:
            return theme.TAB_SELECTED_TEXT_COLOR_STR
        return theme.TAB_TEXT_COLOR_STR

    def set_selected_look(self, selected_b: bool) -> None:
        """Draw the icon in the text color of a selected or other tab.

        Inputs:
            selected_b: True when its tab is selected.
        Outputs: none.
        """
        # LLFR-01147: the icon follows the color of the tab's text.
        self.selected_b = bool(selected_b)
        color_str = self.icon_color_str()
        self.button.setIcon(icons.icon_for(self.icon_name_str, color_str,
                                           color_str))

    def click(self) -> None:
        """Click the button, as the user does.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-01015, LLFR-01028: for the tests.
        self.button.click()

    def toolTip(self) -> str:
        """Return the button tip of the button.

        Inputs: none.
        Outputs: "Undock" or "Dock" (LLFR-01014, LLFR-01027).
        """
        # LLFR-01014, LLFR-01027.
        return self.button.toolTip()

    def icon(self):
        """Return the icon of the button.

        Inputs: none.
        Outputs: the QIcon (LLFR-01013, LLFR-01026).
        """
        # LLFR-01013, LLFR-01026.
        return self.button.icon()


def build_undock_button(parent=None):
    """Return the undock button shown inside a docked tab.

    Inputs:
        parent: optional parent widget.
    Outputs: a TabIconButton with the undock icon and the tip "Undock".
    """
    # LLFR-01012, LLFR-01013, LLFR-01014.
    return TabIconButton(icon_shapes.UNDOCK_ICON_STR, UNDOCK_TIP_STR,
                         UNDOCK_BUTTON_OBJECT_NAME_STR, parent)


def build_dock_button(parent=None):
    """Return the dock button shown inside a tab of an undocked window.

    Inputs:
        parent: optional parent widget.
    Outputs: a TabIconButton with the dock icon and the tip "Dock".
    """
    # LLFR-01025, LLFR-01026, LLFR-01027.
    return TabIconButton(icon_shapes.DOCK_ICON_STR, DOCK_TIP_STR,
                         DOCK_BUTTON_OBJECT_NAME_STR, parent)
