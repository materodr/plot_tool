"""Title at the top of the plot menus (HLFR-00096, HLFR-00108,
HLFR-00109).

The menus of the plot widget (curve, pinned data tip, plot, flag, delta
marker, area, text note, arrow) start with the name of the object they
act on (LLFR-00425, LLFR-00426), drawn in bold in a paler color than the
options (LLFR-00846), above a separator line (LLFR-00845). The title is
a disabled widget action holding a QLabel: a disabled action is never
highlighted by the pointer or the keyboard (LLFR-00849), and clicking it
neither triggers anything nor closes the menu (LLFR-00847, LLFR-00848).
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QWidgetAction

from view import theme
from view.elided_text import menu_title_text

# LLFR-00425: the object name of the title's label, to find it.
MENU_TITLE_OBJECT_NAME_STR = "plot_menu_title"
# LLFR-00846: bold, in the app's paler text color, with the padding of a
# menu option so that it lines up with the options.
MENU_TITLE_COLOR_STR = theme.MUTED_TEXT_COLOR_STR
MENU_TITLE_STYLE_STR = (
    f"QLabel#{MENU_TITLE_OBJECT_NAME_STR} {{ color: "
    f"{MENU_TITLE_COLOR_STR}; font-weight: bold; background: transparent; "
    "padding: 5px 24px 5px 14px; }")


def add_menu_title(menu, name_str: str):
    """Put the title and a separator at the top of an empty menu.

    Inputs:
        menu: the QMenu, with no action yet.
        name_str: the name of the object the menu acts on.
    Outputs: the QWidgetAction of the title. It has no data, so no
        request is attached to it.
    """
    # LLFR-00426, LLFR-00850: the name, shortened in the middle past 40
    # characters, shown literally.
    label = QLabel(menu_title_text(name_str))
    label.setObjectName(MENU_TITLE_OBJECT_NAME_STR)
    label.setTextFormat(Qt.TextFormat.PlainText)
    # LLFR-00846: bold and paler than the options.
    title_font = label.font()
    title_font.setBold(True)
    label.setFont(title_font)
    label.setStyleSheet(MENU_TITLE_STYLE_STR)
    title_action = QWidgetAction(menu)
    title_action.setDefaultWidget(label)
    # LLFR-00426: the action carries the title text too, for screen
    # readers and checks; the label is what is drawn.
    title_action.setText(label.text())
    # LLFR-00847 to LLFR-00849: a disabled action does nothing when
    # clicked, keeps the menu open and is never highlighted.
    title_action.setEnabled(False)
    menu.addAction(title_action)
    # LLFR-00845: a separator line between the title and the options.
    menu.addSeparator()
    return title_action


def is_menu_title(action) -> bool:
    """Tell whether a menu action is the title of a plot menu.

    Inputs:
        action: a QAction.
    Outputs: True for an action made by add_menu_title.
    """
    # LLFR-00425: tests and callers tell the title from the options.
    if not isinstance(action, QWidgetAction):
        return False
    label = action.defaultWidget()
    return (label is not None
            and label.objectName() == MENU_TITLE_OBJECT_NAME_STR)


def menu_title_label(menu):
    """Return the label of the title of a plot menu.

    Inputs:
        menu: a QMenu.
    Outputs: the QLabel of its title, or None when it has none.
    """
    # LLFR-00426: for checks of the title's text and look.
    for action in menu.actions():
        if is_menu_title(action):
            return action.defaultWidget()
    return None
