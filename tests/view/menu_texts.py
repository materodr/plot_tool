"""The texts of the plot menus, in their required order, shared by the
view tests (LLFR-00046, LLFR-00090, LLFR-00175, LLFR-00314, LLFR-00378).

Every plot menu starts with a title and a separator (LLFR-00425,
LLFR-00845); menu_option_texts leaves both out, so that the lists below
are the options only.

Inputs: none (module of constants and one helper).
"""


def menu_option_texts(menu) -> list:
    """Return the texts of the options of a menu, in order.

    Inputs:
        menu: a QMenu.
    Outputs: the texts of its top-level actions, without the title of a
        plot menu (LLFR-00425) and without separators.
    """
    from view.menu_title import is_menu_title
    return [action.text() for action in menu.actions()
            if not action.isSeparator() and not is_menu_title(action)]


# LLFR-00046, LLFR-00412, LLFR-00413: the pinned data tip menu.
TIP_MENU_TEXT_LIST = ["Delete", "Delete all data tips in this plot",
                      "Delete all data tips in all plots"]
# LLFR-00087, LLFR-00391, LLFR-00090, LLFR-00416: the flag menu.
FLAG_MENU_TEXT_LIST = ["Rename", "Color", "Delete", "Delete all flags"]
# LLFR-00175, LLFR-00429, LLFR-00409, LLFR-00414, LLFR-00415: the delta
# marker menu.
DELTA_MENU_TEXT_LIST = ["Rename", "Color", "Delete",
                        "Delete all delta markers in this plot",
                        "Delete all delta markers in all plots"]
# LLFR-00314, LLFR-00417: the area menu.
AREA_MENU_TEXT_LIST = ["Rename", "Color", "Delete", "Delete all areas",
                       "Delete plot"]
# LLFR-00378: the arrow menu.
ARROW_MENU_TEXT_LIST = ["Rename", "Color", "Delete"]
