"""Shorten a text in the middle with "..." (no Qt needed).

The file name line of the signal list panel (LLFR-00362) shows the
name of the opened data file. When the name is wider than the panel,
it is shortened in the middle, so that both its start and its extension
stay visible. The width of a text is measured by a function given by
the caller (QFontMetrics.horizontalAdvance in the view), so this module
can be tested without Qt.
"""

# LLFR-00362: the text put in place of the left-out middle of the name.
ELLIPSIS_TEXT_STR = "..."


def middle_elided_text(text_str: str, available_width_i: int,
                       text_width_function) -> str:
    """Return the text, shortened in the middle when it is too wide.

    Inputs:
        text_str: the whole text.
        available_width_i: the width the text may take, in pixels.
        text_width_function: function taking a str and returning its
            width in pixels (int).
    Outputs: text_str itself when it fits; otherwise the longest text
        made of a start of text_str, "..." and an end of text_str that
        fits, with the start one character longer than the end when the
        kept characters are odd; "..." alone when nothing else fits.
    """
    # LLFR-00362: a name that fits is shown whole.
    if text_width_function(text_str) <= available_width_i:
        return text_str
    # LLFR-00362: keep as many characters as fit, half from the start
    # and half from the end, around "...".
    for kept_count_i in range(len(text_str) - 1, 0, -1):
        start_count_i = (kept_count_i + 1) // 2
        end_count_i = kept_count_i - start_count_i
        # An end of 0 characters is text_str[len:], the empty text.
        end_str = text_str[len(text_str) - end_count_i:]
        candidate_str = (text_str[:start_count_i] + ELLIPSIS_TEXT_STR
                         + end_str)
        if text_width_function(candidate_str) <= available_width_i:
            return candidate_str
    return ELLIPSIS_TEXT_STR


def is_elided(shown_text_str: str, whole_text_str: str) -> bool:
    """Tell whether a shown text is a shortened version of the whole one.

    Inputs:
        shown_text_str: the text shown on screen.
        whole_text_str: the whole text.
    Outputs: True when the shown text differs from the whole text.
    """
    # LLFR-00362: the tip with the whole name is only needed when the
    # name was shortened.
    return shown_text_str != whole_text_str


# LLFR-00850: the longest title of a plot menu, in characters.
MENU_TITLE_MAXIMUM_LENGTH_I = 40


def menu_title_text(name_str: str) -> str:
    """Return the title of a plot menu for the name of its object.

    Inputs:
        name_str: the name of the object the menu acts on (LLFR-00426).
    Outputs: the name itself when it has at most 40 characters; else a
        text of 40 characters made of its start, "..." and its end
        (LLFR-00850).
    """
    # LLFR-00426: the title is the object's name; LLFR-00850: a long
    # one is shortened in the middle, each character counting as 1.
    return middle_elided_text(str(name_str), MENU_TITLE_MAXIMUM_LENGTH_I,
                              len)
