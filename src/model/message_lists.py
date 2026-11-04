"""Text of the boxes that list several separate items.

Every information, error or question box that lists several separate
items (LLFR-00978) shows them in the same way, built here so that all
the boxes look the same:

- two or more items are numbered ``1.``, ``2.`` and so on (LLFR-00977),
  with one blank line between one item and the next (LLFR-00979);
- the sentence that introduces the list, when there is one, stays above
  it, followed by one blank line (LLFR-00980);
- one item alone is shown without a number (LLFR-00981);
- the lines after the first line of an item are indented below the
  start of its text (LLFR-00982);
- the numbers are aligned on their right side (LLFR-00983);
- the load report numbers the items under each of its headings as their
  own list (LLFR-00984, LLFR-00985, LLFR-00986).

The functions only build plain text, so the model, the controllers and
the view can all use them (COR-00003).
"""

# LLFR-00983: a figure space has the width of a digit in the fonts of
# the boxes, so that a number padded with it on its left ends where the
# longest number of the list ends.
FIGURE_SPACE_STR = " "
# LLFR-00982: a punctuation space has the width of the period after the
# number, so that a sub-line starts where the text of the first line
# starts.
PUNCTUATION_SPACE_STR = " "
# LLFR-00977: the number of an item, followed by a period and a space.
NUMBER_FORMAT_STR = "{number}. "
# LLFR-00979, LLFR-00980, LLFR-00986: one blank line between the parts.
BLANK_LINE_SEPARATOR_STR = "\n\n"
LINE_SEPARATOR_STR = "\n"


def number_prefix(number_i: int, width_i: int) -> str:
    """Return the number written in front of an item.

    Inputs:
        number_i: the number of the item, from 1.
        width_i: the number of digits of the largest number of the list.
    Outputs: the number, padded on its left with figure spaces up to
        width_i digits, a period and a space, for example " 1. "
        with width 2.
    """
    # LLFR-00977, LLFR-00983: the numbers end at the same place.
    number_str = str(int(number_i))
    padding_str = FIGURE_SPACE_STR * max(0, int(width_i) - len(number_str))
    return padding_str + NUMBER_FORMAT_STR.format(number=number_str)


def sub_line_indent(width_i: int) -> str:
    """Return the indent of the lines after the first line of an item.

    Inputs:
        width_i: the number of digits of the largest number of the list.
    Outputs: blank characters as wide as the number of LLFR-00977 with
        its period and its space.
    """
    # LLFR-00982: the sub-lines start below the text of the first line.
    return FIGURE_SPACE_STR * int(width_i) + PUNCTUATION_SPACE_STR + " "


def numbered_item_text(item_str: str, number_i: int, width_i: int) -> str:
    """Return one item with its number and its indented sub-lines.

    Inputs:
        item_str: the text of the item; it may hold several lines.
        number_i: the number of the item, from 1.
        width_i: the number of digits of the largest number of the list.
    Outputs: the first line after its number, and every other line
        after the indent of LLFR-00982.
    """
    # LLFR-00977, LLFR-00982: number the first line, indent the others.
    line_list = str(item_str).split(LINE_SEPARATOR_STR)
    indent_str = sub_line_indent(width_i)
    return LINE_SEPARATOR_STR.join(
        [number_prefix(number_i, width_i) + line_list[0]]
        + [indent_str + line_str for line_str in line_list[1:]])


def list_body_text(item_list: list, numbered_b: bool = None) -> str:
    """Return the items of one list, without a heading.

    Inputs:
        item_list: the texts of the items, in the order of the list.
        numbered_b: True to number the items, False to leave them
            unnumbered; None numbers them only when there are two or
            more (LLFR-00977, LLFR-00981).
    Outputs: the items separated by one blank line (LLFR-00979); "" for
        an empty list.
    """
    # LLFR-00977, LLFR-00981: two or more items are numbered.
    text_list = [str(item_str) for item_str in item_list]
    if numbered_b is None:
        numbered_b = len(text_list) >= 2
    if not numbered_b:
        # LLFR-00981: one item alone keeps its text as it is.
        return BLANK_LINE_SEPARATOR_STR.join(text_list)
    # LLFR-00983: every number is as wide as the largest one.
    width_i = len(str(len(text_list)))
    # LLFR-00979: one blank line between one item and the next.
    return BLANK_LINE_SEPARATOR_STR.join(
        numbered_item_text(item_str, index_i + 1, width_i)
        for index_i, item_str in enumerate(text_list))


def list_text(item_list: list, heading_str: str = "",
              numbered_b: bool = None) -> str:
    """Return the text of a box that lists several separate items.

    Inputs:
        item_list: the texts of the items, in the order of the list.
        heading_str: the sentence that introduces the list, or "".
        numbered_b: as in list_body_text.
    Outputs: the heading, one blank line and the items of
        list_body_text (LLFR-00980); only the items when there is no
        heading; only the heading when there is no item.
    """
    # LLFR-00980: the heading stays above the list, then a blank line.
    body_str = list_body_text(item_list, numbered_b)
    part_list = [part_str for part_str in (str(heading_str), body_str)
                 if part_str]
    return BLANK_LINE_SEPARATOR_STR.join(part_list)


def sections_text(section_list: list) -> str:
    """Return the text of a box whose items are grouped under headings.

    Inputs:
        section_list: (heading_str, item list) tuples, in the order of
            the box; a section with no item is left out.
    Outputs: each heading followed by its own list (LLFR-00984), with
        one blank line between one section and the next (LLFR-00986);
        every item is numbered when the box lists two or more items in
        all (LLFR-00985), and none when it lists only one (LLFR-00981).
    """
    # LLFR-00985, LLFR-00981: the count of the whole box decides.
    kept_list = [(str(heading_str), list(item_list))
                 for heading_str, item_list in section_list if item_list]
    item_count_i = sum(len(item_list) for _, item_list in kept_list)
    numbered_b = item_count_i >= 2
    # LLFR-00984, LLFR-00986: each heading starts its own numbering, and
    # one blank line separates the sections.
    return BLANK_LINE_SEPARATOR_STR.join(
        list_text(item_list, heading_str, numbered_b)
        for heading_str, item_list in kept_list)
