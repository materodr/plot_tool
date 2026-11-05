"""Type names of the objects and the titles of their menus (no Qt).

Every kind of object of the plots and of the signal list has one type
name (LLFR-01244), kept in TYPE_NAME_DICT so that the code uses it from
one source. The title of a right-click menu is the type name, a colon,
a space and the label of the object, for example ``Flag: Flag 1``
(LLFR-00426); a label longer than 40 characters is shortened in the
middle with "…" (LLFR-00850, LLFR-01249), and the view shows the whole
label in a tip (LLFR-01246).
"""

# LLFR-01244: the kinds of objects, as the code names them.
FLAG_OBJECT_STR = "flag"
AREA_OBJECT_STR = "area"
DELTA_X_OBJECT_STR = "delta_x"
DELTA_Y_OBJECT_STR = "delta_y"
ARROW_OBJECT_STR = "arrow"
CIRCLE_OBJECT_STR = "circle"
RECTANGLE_OBJECT_STR = "rectangle"
TEXT_NOTE_OBJECT_STR = "text_note"
DATA_TIP_OBJECT_STR = "data_tip"
CURVE_OBJECT_STR = "curve"
PLOT_OBJECT_STR = "plot"
TAB_OBJECT_STR = "tab"
SIGNAL_OBJECT_STR = "signal"
FILE_OBJECT_STR = "file"
# LLFR-01244: the one table of the type names.
TYPE_NAME_DICT = {
    FLAG_OBJECT_STR: "Flag",
    AREA_OBJECT_STR: "Vert Area",
    DELTA_X_OBJECT_STR: "Delta X",
    DELTA_Y_OBJECT_STR: "Delta Y",
    ARROW_OBJECT_STR: "Arrow",
    CIRCLE_OBJECT_STR: "Circle",
    RECTANGLE_OBJECT_STR: "Rectangle",
    TEXT_NOTE_OBJECT_STR: "Text",
    DATA_TIP_OBJECT_STR: "Data Tip",
    CURVE_OBJECT_STR: "Curve",
    PLOT_OBJECT_STR: "Plot",
    TAB_OBJECT_STR: "Tab",
    SIGNAL_OBJECT_STR: "Signal",
    FILE_OBJECT_STR: "File",
}
# LLFR-00850: the longest label of a menu title, in characters, and the
# one character put in place of its left-out middle.
TITLE_LABEL_MAXIMUM_LENGTH_I = 40
TITLE_ELLIPSIS_STR = "…"
# LLFR-01245: the text after the first word of a text note's label.
NOTE_LABEL_ELLIPSIS_STR = "…"


def type_name(object_kind_str: str) -> str:
    """Return the type name of a kind of object.

    Inputs:
        object_kind_str: one of the *_OBJECT_STR kinds.
    Outputs: its type name, for example "Vert Area" for an area.
    Raises: KeyError for an unknown kind.
    """
    # LLFR-01244: one name per kind, from the one table.
    return TYPE_NAME_DICT[object_kind_str]


def shortened_label(label_str: str) -> str:
    """Return a label shortened in the middle when it is too long.

    Inputs:
        label_str: the whole label.
    Outputs: the label itself when it has at most 40 characters; else
        40 characters: its start, "…" and its end, the start one
        character longer than the end when they differ.
    """
    # LLFR-00850, LLFR-01249: each character counts as 1.
    whole_str = str(label_str)
    if len(whole_str) <= TITLE_LABEL_MAXIMUM_LENGTH_I:
        return whole_str
    kept_count_i = TITLE_LABEL_MAXIMUM_LENGTH_I - len(TITLE_ELLIPSIS_STR)
    start_count_i = (kept_count_i + 1) // 2
    end_count_i = kept_count_i - start_count_i
    return (whole_str[:start_count_i] + TITLE_ELLIPSIS_STR
            + whole_str[len(whole_str) - end_count_i:])


def menu_title_text(object_kind_str: str, label_str: str = "") -> str:
    """Return the title of the menu of an object.

    Inputs:
        object_kind_str: one of the *_OBJECT_STR kinds.
        label_str: the label of the object; "" for an object with no
            label (a plot).
    Outputs: ``<type name>: <label>`` with the label shortened as in
        shortened_label; the type name alone when there is no label.
    """
    # LLFR-00426, LLFR-01247, LLFR-01250, LLFR-01251: the type name, a
    # colon, a space and the label; a plot has no label.
    name_str = type_name(object_kind_str)
    if not str(label_str):
        return name_str
    return f"{name_str}: {shortened_label(label_str)}"


def is_label_shortened(label_str: str) -> bool:
    """Tell whether a label is shortened in its menu title.

    Inputs:
        label_str: the whole label.
    Outputs: True when it has more than 40 characters.
    """
    # LLFR-01246: the whole label then shows in a tip.
    return shortened_label(label_str) != str(label_str)


def text_note_label(text_str: str) -> str:
    """Return the label of a text note in its menu title.

    Inputs:
        text_str: the text of the note.
    Outputs: its first word followed by "…", or the whole text when it
        is one word.
    """
    # LLFR-01245: words are separated by spaces and line breaks.
    word_list = str(text_str).split()
    if not word_list:
        return ""
    if len(word_list) == 1:
        return word_list[0]
    return word_list[0] + NOTE_LABEL_ELLIPSIS_STR
