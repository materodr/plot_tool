"""Title at the top of the plot menus (HLFR-00096, HLFR-00108,
HLFR-00109).

The menus of the plot widget (curve, pinned data tip, plot, flag, delta
marker, area, text note, arrow, shape), of the tabs and of the signal
list start with the type name and the label of the object they act on
(LLFR-00425, LLFR-00426, LLFR-01247, LLFR-01250, LLFR-01251), drawn
in bold in a paler color than the options (LLFR-00846), above a
separator line (LLFR-00845). The title is
a disabled widget action holding a QLabel: a disabled action is never
highlighted by the pointer or the keyboard (LLFR-00849), and clicking it
neither triggers anything nor closes the menu (LLFR-00847, LLFR-00848).
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QWidgetAction

from model import object_names
from view import theme

# LLFR-00425: the object name of the title's label, to find it.
MENU_TITLE_OBJECT_NAME_STR = "plot_menu_title"
# LLFR-00846: bold, in the app's paler text color, with the padding of a
# menu option so that it lines up with the options.
MENU_TITLE_COLOR_STR = theme.MUTED_TEXT_COLOR_STR
MENU_TITLE_STYLE_STR = (
    f"QLabel#{MENU_TITLE_OBJECT_NAME_STR} {{ color: "
    f"{MENU_TITLE_COLOR_STR}; font-weight: bold; background: transparent; "
    "padding: 5px 24px 5px 14px; }")


def add_menu_title(menu, object_kind_str: str, label_str: str = ""):
    """Put the title and a separator at the top of an empty menu.

    Inputs:
        menu: the QMenu, with no action yet.
        object_kind_str: the kind of the object the menu acts on, one of
            the *_OBJECT_STR kinds of model.object_names.
        label_str: the label of the object, "" for none (a plot).
    Outputs: the QWidgetAction of the title. It has no data, so no
        request is attached to it.
    """
    # LLFR-00426, LLFR-01247, LLFR-01250, LLFR-01251: the type name, a
    # colon and the label, shortened in the middle past 40 characters
    # (LLFR-00850, LLFR-01249), shown literally.
    label = QLabel(object_names.menu_title_text(object_kind_str, label_str))
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
    # LLFR-01246: the whole label in a tip when it was shortened; the
    # menu shows the tips of its actions, the disabled title's too.
    if object_names.is_label_shortened(label_str):
        label.setToolTip(str(label_str))
        title_action.setToolTip(str(label_str))
        menu.setToolTipsVisible(True)
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
