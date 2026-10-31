"""Search of signal names in the signal list (HLFR-00033, HLFR-00034).

The typed text is split into search words at spaces (LLFR-00105). Each
word and each signal name is compared without case (LLFR-00098) and
without separators (LLFR-00100). A word matches a name when it appears
anywhere in it (LLFR-00099), or, for words of 4 or more characters,
when a part of the name is within the typo allowance (LLFR-00101).
The matching names are returned in the three groups of LLFR-00102.

This module is pure Python and has no user interface code (COR-00009).
"""

# LLFR-00097: text the view shows when no signal matches.
NO_MATCH_TEXT_STR = "No matching signals"

# LLFR-00100: characters ignored in the typed text and in the names.
# Spaces are also ignored in names; in the typed text they separate the
# search words (LLFR-00105) before this table is applied.
IGNORED_CHARACTER_TABLE_DICT = str.maketrans("", "", " _-.")

# LLFR-00101: one typo is allowed for every full block of this many
# characters of a search word.
CHARACTERS_PER_TYPO_I = 4

# LLFR-00102: values returned by word_match_kind.
EXACT_MATCH_STR = "exact"
TYPO_MATCH_STR = "typo"
NO_MATCH_STR = ""


def normalize_text(text_str: str) -> str:
    """Bring a text into the form used to compare words and names.

    Inputs:
        text_str: a signal name or a search word.
    Outputs: the text in lowercase, without spaces, underscores, hyphens
        and dots.
    """
    # LLFR-00098: case is ignored. LLFR-00100: separators are ignored.
    return text_str.lower().translate(IGNORED_CHARACTER_TABLE_DICT)


def split_search_words(text_str: str) -> list:
    """Split the typed text into normalized search words.

    Inputs:
        text_str: the text typed in the search box.
    Outputs: a list of the normalized words, in typed order. Words that
        are empty after normalizing (for example "_") are dropped.
    """
    # LLFR-00105: the text is split at each space; repeated spaces give
    # empty words, which are dropped.
    word_list = []
    for raw_word_str in text_str.split(" "):
        # LLFR-00098, LLFR-00100: each word is normalized.
        word_str = normalize_text(raw_word_str)
        if word_str:
            word_list.append(word_str)
    return word_list


def allowed_typo_count(word_str: str) -> int:
    """Return how many typos a search word may have.

    Inputs:
        word_str: a normalized search word.
    Outputs: 0 for words of 1 to 3 characters, otherwise one typo for
        every full 4 characters (1 for 4 to 7, 2 for 8 to 11, ...).
    """
    # LLFR-00101: words shorter than 4 characters only match exactly.
    if len(word_str) < CHARACTERS_PER_TYPO_I:
        return 0
    return len(word_str) // CHARACTERS_PER_TYPO_I


def has_close_substring(word_str: str, name_str: str,
                        maximum_distance_i: int) -> bool:
    """Check if some part of a name is close enough to a search word.

    The edit distance counts wrong, missing and extra characters. The
    part of the name may start and end anywhere. The check uses the
    bit-parallel algorithm of Myers (1999), which processes one name
    character per step, so it stays fast for long names.

    Inputs:
        word_str: a normalized, non-empty search word.
        name_str: a normalized signal name.
        maximum_distance_i: largest edit distance accepted.
    Outputs: True if some part of name_str is at most
        maximum_distance_i edits away from word_str, else False.
    """
    # LLFR-00101: the empty part of the name is within the distance
    # when the whole word may be missing.
    word_length_i = len(word_str)
    if word_length_i <= maximum_distance_i:
        return True
    # LLFR-00101: bit masks of the positions of each character in the
    # word (bit i is set when word_str[i] is that character).
    position_mask_dict = {}
    for position_i, character_str in enumerate(word_str):
        position_mask_dict[character_str] = (
            position_mask_dict.get(character_str, 0) | (1 << position_i))
    all_bits_i = (1 << word_length_i) - 1
    last_bit_i = 1 << (word_length_i - 1)
    positive_vertical_i = all_bits_i
    negative_vertical_i = 0
    # LLFR-00101: distance between the whole word and the best part of
    # the name that ends at the current name character.
    distance_i = word_length_i
    for character_str in name_str:
        equal_i = position_mask_dict.get(character_str, 0)
        vertical_change_i = equal_i | negative_vertical_i
        horizontal_change_i = (
            (((equal_i & positive_vertical_i) + positive_vertical_i)
             ^ positive_vertical_i) | equal_i)
        positive_horizontal_i = negative_vertical_i | (
            ~(horizontal_change_i | positive_vertical_i) & all_bits_i)
        negative_horizontal_i = positive_vertical_i & horizontal_change_i
        if positive_horizontal_i & last_bit_i:
            distance_i += 1
        elif negative_horizontal_i & last_bit_i:
            distance_i -= 1
        # LLFR-00101: the part of the name may start anywhere, so the
        # top row of the distance table stays 0 (no bit shifted in).
        positive_horizontal_i = (positive_horizontal_i << 1) & all_bits_i
        negative_horizontal_i = (negative_horizontal_i << 1) & all_bits_i
        positive_vertical_i = negative_horizontal_i | (
            ~(vertical_change_i | positive_horizontal_i) & all_bits_i)
        negative_vertical_i = positive_horizontal_i & vertical_change_i
        if distance_i <= maximum_distance_i:
            return True
    return False


def word_match_kind(word_str: str, normalized_name_str: str) -> str:
    """Tell how a search word matches a signal name.

    Inputs:
        word_str: a normalized search word (see split_search_words).
        normalized_name_str: a signal name after normalize_text.
    Outputs: "exact" if the word appears in the name, "typo" if it only
        matches within the typo allowance, or "" if it does not match.
    """
    # LLFR-00099: the word may appear anywhere in the name.
    if word_str in normalized_name_str:
        return EXACT_MATCH_STR
    # LLFR-00101: words of 4 or more characters also match a part of
    # the name that is within the typo allowance.
    allowed_typos_i = allowed_typo_count(word_str)
    if allowed_typos_i > 0 and has_close_substring(
            word_str, normalized_name_str, allowed_typos_i):
        return TYPO_MATCH_STR
    return NO_MATCH_STR


def search_signals(signal_name_list: list, text_str: str) -> list:
    """Return the signal names that match the typed text, in order.

    Inputs:
        signal_name_list: the signal names of the file, in file order.
        text_str: the text typed in the search box.
    Outputs: a list of the matching names: first the names that match
        every word exactly and start with the first word, then the
        other exact matches, then the names that need the typo
        allowance, each group in file order. An empty or spaces-only
        text returns all names in file order. No match returns [].
    """
    # LLFR-00096: an empty or spaces-only text shows all signals.
    word_list = split_search_words(text_str)
    if not word_list:
        return list(signal_name_list)
    first_word_str = word_list[0]
    starts_with_first_word_list = []
    other_exact_list = []
    typo_list = []
    for signal_name_str in signal_name_list:
        # LLFR-00098, LLFR-00100: names are compared normalized.
        normalized_name_str = normalize_text(signal_name_str)
        # LLFR-00105: every word must match, in any order.
        needs_typo_b = False
        matches_b = True
        for word_str in word_list:
            match_kind_str = word_match_kind(word_str, normalized_name_str)
            if match_kind_str == NO_MATCH_STR:
                matches_b = False
                break
            if match_kind_str == TYPO_MATCH_STR:
                needs_typo_b = True
        if not matches_b:
            continue
        # LLFR-00102: three groups, file order kept inside each group.
        if needs_typo_b:
            typo_list.append(signal_name_str)
        elif normalized_name_str.startswith(first_word_str):
            starts_with_first_word_list.append(signal_name_str)
        else:
            other_exact_list.append(signal_name_str)
    # LLFR-00097: no match gives an empty list; the view then shows
    # NO_MATCH_TEXT_STR.
    return starts_with_first_word_list + other_exact_list + typo_list
