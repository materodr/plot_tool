"""The background of the texts on the plots, with no Qt (HLFR-00167).

One choice for all the texts of all the plots (LLFR-01420): "Transparent"
or "Auto contrast" (LLFR-01418). The workspace keeps it, so that an undo
puts it back (LLFR-01427); the view keeps it in the app's settings
between launches (LLFR-01426) and draws the texts with it.
"""

# LLFR-01418: the two choices, in the order of the submenu.
TRANSPARENT_STR = "transparent"
AUTO_CONTRAST_STR = "auto_contrast"
TEXT_BACKGROUND_TUPLE = (TRANSPARENT_STR, AUTO_CONTRAST_STR)
# LLFR-01425: the choice when the settings hold none.
DEFAULT_TEXT_BACKGROUND_STR = AUTO_CONTRAST_STR
# LLFR-01418: the texts of the submenu.
TEXT_BACKGROUND_TEXT_DICT = {
    TRANSPARENT_STR: "Transparent",
    AUTO_CONTRAST_STR: "Auto contrast",
}


def cleaned_text_background(stored_value) -> str:
    """Return a usable text background choice.

    Inputs:
        stored_value: a value read from the settings or a snapshot: any
            type, or None.
    Outputs: one of TEXT_BACKGROUND_TUPLE; DEFAULT_TEXT_BACKGROUND_STR
        for any other value.
    """
    # LLFR-01425: no value, or another value, gives "Auto contrast".
    if isinstance(stored_value, str):
        choice_str = stored_value.strip().lower()
        if choice_str in TEXT_BACKGROUND_TUPLE:
            return choice_str
    return DEFAULT_TEXT_BACKGROUND_STR
