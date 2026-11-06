"""Draw the feature and fix flow of plot_tool as an SVG image.

Usage:
    python docs/process/make_feature_fix_flow.py

The script writes docs/process/feature_fix_flow.svg, the flow of
docs/process/feature_fix_flow.md, with a fixed, aligned layout: one main
column of steps, the return rails on its right and a legend on its left.
docs/process/feature_fix_flow.png is a render of that SVG at twice its
size. When a step of the flow changes, change STEP_LIST and the other
tables below, run the script and render the PNG again (PCR-00114).

It uses only the standard library.
"""

import html
import os

OUTPUT_PATH_STR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "feature_fix_flow.svg")
IMAGE_WIDTH_I = 1500
CENTRE_X_I = 540          # centre of the main column
BOX_WIDTH_I = 600         # box width
BOX_GAP_I = 34            # vertical gap between boxes
RAIL_X_LIST = [900, 940, 980, 1020]   # x of the return rails (right side)
# The fill, border and text colours of each kind of step.
COLOUR_DICT = {
    "owner": ("#fde7c8", "#c77700", "#000"),
    "impl": ("#dbeafe", "#1d4ed8", "#000"),
    "rev": ("#dcfce7", "#15803d", "#000"),
    "ci": ("#ede9fe", "#6d28d9", "#000"),
    "done": ("#e5e7eb", "#374151", "#000"),
    "frozen": ("#fff5f5", "#b91c1c", "#b91c1c"),
}
# (id, kind, shape, lines) of each step, from top to bottom.
STEP_LIST = [
    ("1", "owner", "box", ["1. Feature or Fix issue, from its template",
                           "Fix: bug description, severity, steps to "
                           "reproduce"]),
    ("2", "owner", "box", ["2. Owner approves HLFR, PCR and COR texts, if "
                           "any", "edge cases listed · direct link"]),
    ("3", "impl", "box", ["3. Branch feature/<n>-… or fix/<n>-… from "
                          "develop", "own worktree"]),
    ("4", "owner", "box", ["4. FIRST QUESTION BATCH to the owner",
                           "before any code or test · recorded in the "
                           "issue Q&A"]),
    ("5a", "impl", "box", ["5a. Requirement revision",
                           "check_requirements = 0 problems"]),
    ("5b", "impl", "box", ["5b. Code"]),
    ("5c", "impl", "box", ["5c. Tests the implementer deems necessary",
                           "no PyPI: packages from ci-wheels first",
                           "Fix: a test that reproduces the bug"]),
    ("5d", "impl", "box", ["5d. Branch up to date with develop?",
                           "if not, bring develop in"]),
    ("5e", "impl", "dec", ["5e. New questions?"]),
    ("6", "impl", "dec", ["6. Handover?",
                          "no questions · satisfied · branch up to date"]),
    ("F1", "frozen", "frz", ["IMPLEMENTER FROZEN — changes nothing"]),
    ("7", "rev", "box", ["7. Analyses code · requirements · tests · issue "
                         "Q&A", "Fix: checks the bug-reproducing test"]),
    ("8", "rev", "box", ["8. Adds its own tests (tests/ only)"]),
    ("9", "rev", "box", ["9. Runs the tests it deems necessary",
                         "no PyPI: packages from ci-wheels first"]),
    ("10", "rev", "dec", ["10–12. No findings?",
                          "Branch still up to date?"]),
    ("F2", "frozen", "frz", ["GREEN LIGHT — BRANCH FROZEN · nobody "
                             "changes it"]),
    ("13", "rev", "box", ["13. Open the PR into develop",
                          "Fail* section (or 'none') · Req. validation",
                          "Closes #n · Green light: <SHA>"]),
    ("14", "ci", "dec", ["14. CI: full suite once, in parallel shards",
                         "collected by 'tests' + requirement checks",
                         "(docs-only PR: suite skipped)"]),
    ("18", "rev", "box", ["18. Issue sections filled",
                          "Feature: How · Tests used · Evidence  |  Fix: "
                          "Solution · How tested · Evidence"]),
    ("19", "rev", "box", ["19. Reviewer merges into develop",
                          "CI passed, or only declared Fail*"]),
    ("20", "done", "box", ["20. Owner told, with the link"]),
]
# The label of the arrow that leaves a decision downwards.
DOWN_LABEL_DICT = {"5e": "no", "6": "yes", "10": "yes",
                   "14": "pass / only declared Fail*"}
# (from, rail, colour, dashed, label lines) of each return to step 5a.
RETURN_LIST = [
    ("5e", 0, "#1d4ed8", False, ["yes: one batch to the owner,",
                                 "recorded in the issue"]),
    ("6", 1, "#1d4ed8", False, ["not yet"]),
    ("10", 2, "#b91c1c", True, ["findings → reject",
                                "develop moved → outdated"]),
    ("14", 3, "#b91c1c", True, ["15. commit after CI started → CI stops",
                                "16. develop moved → outdated",
                                "17. CI fails → reject"]),
]


def escape(text_str: str) -> str:
    """Escape a text for the SVG.

    Inputs:
        text_str: the text to show.
    Outputs: the text with the characters of XML escaped.
    """
    return html.escape(text_str)


def step_positions() -> tuple:
    """Place the steps of STEP_LIST from top to bottom.

    Inputs: none.
    Outputs: a tuple (positions, image height), where positions is a dict
        from each step ID to (top, height, shape, kind, lines).
    """
    position_dict = {}
    top_i = 110
    for step_id_str, kind_str, shape_str, line_list in STEP_LIST:
        height_i = 30 + 20 * len(line_list) if shape_str != "frz" else 40
        if shape_str == "dec":
            height_i = 34 + 20 * len(line_list)
        if step_id_str in ("4", "7"):
            top_i += 26
        position_dict[step_id_str] = (top_i, height_i, shape_str, kind_str,
                                      line_list)
        top_i += (height_i + BOX_GAP_I
                  + (26 if step_id_str in ("6", "10") else 0))
    return position_dict, top_i + 40


def draw_step(part_list: list, position_dict: dict, step_id_str: str) -> None:
    """Draw one step: a box, a decision or a frozen state, with its text.

    Inputs:
        part_list: the SVG parts drawn so far, extended in place.
        position_dict: the positions of step_positions.
        step_id_str: the ID of the step.
    Outputs: none.
    """
    top_f, height_i, shape_str, kind_str, line_list = (
        position_dict[step_id_str])
    fill_str, stroke_str, text_colour_str = COLOUR_DICT[kind_str]
    left_f = CENTRE_X_I - BOX_WIDTH_I / 2
    if shape_str == "dec":
        corner_i = 28
        point_str = (f"{left_f},{top_f+height_i/2} {left_f+corner_i},{top_f} "
                     f"{left_f+BOX_WIDTH_I-corner_i},{top_f} "
                     f"{left_f+BOX_WIDTH_I},{top_f+height_i/2} "
                     f"{left_f+BOX_WIDTH_I-corner_i},{top_f+height_i} "
                     f"{left_f+corner_i},{top_f+height_i}")
        part_list.append(f'<polygon points="{point_str}" fill="{fill_str}" '
                         f'stroke="{stroke_str}" stroke-width="1.6"/>')
    else:
        dash_str = ' stroke-dasharray="6 4"' if shape_str == "frz" else ""
        part_list.append(f'<rect x="{left_f}" y="{top_f}" '
                         f'width="{BOX_WIDTH_I}" height="{height_i}" '
                         f'rx="12" fill="{fill_str}" stroke="{stroke_str}" '
                         f'stroke-width="1.6"{dash_str}/>')
    line_count_i = len(line_list)
    for index_i, line_str in enumerate(line_list):
        text_y_f = (top_f + height_i / 2
                    + (index_i - (line_count_i - 1) / 2) * 20 + 5)
        weight_str = "600" if index_i == 0 else "400"
        part_list.append(f'<text x="{CENTRE_X_I}" y="{text_y_f}" '
                         f'text-anchor="middle" font-size="15" '
                         f'font-weight="{weight_str}" '
                         f'fill="{text_colour_str}">{escape(line_str)}'
                         '</text>')


def draw_arrow(part_list: list, start_x_f: float, start_y_f: float,
               end_x_f: float, end_y_f: float, colour_str: str = "#444",
               dashed_b: bool = False) -> None:
    """Draw a straight arrow.

    Inputs:
        part_list: the SVG parts drawn so far, extended in place.
        start_x_f, start_y_f: the start of the arrow.
        end_x_f, end_y_f: the point of the arrow.
        colour_str: its colour, which also names its arrowhead.
        dashed_b: True for a dashed line.
    Outputs: none.
    """
    dash_str = ' stroke-dasharray="7 5"' if dashed_b else ""
    part_list.append(f'<line x1="{start_x_f}" y1="{start_y_f}" '
                     f'x2="{end_x_f}" y2="{end_y_f}" stroke="{colour_str}" '
                     f'stroke-width="1.6"{dash_str} '
                     f'marker-end="url(#a{colour_str[1:]})"/>')


def draw_cluster(part_list: list, position_dict: dict, first_id_str: str,
                 last_id_str: str, colour_str: str, title_str: str) -> None:
    """Draw a dashed frame around a group of steps, with a side title.

    Inputs:
        part_list: the SVG parts drawn so far, extended in place.
        position_dict: the positions of step_positions.
        first_id_str, last_id_str: the first and last steps of the group.
        colour_str: the colour of the frame and its title.
        title_str: the title, written upwards on the left of the frame.
    Outputs: none.
    """
    top_i = position_dict[first_id_str][0] - 34
    bottom_i = (position_dict[last_id_str][0]
                + position_dict[last_id_str][1] + 16)
    left_f = CENTRE_X_I - BOX_WIDTH_I / 2 - 24
    right_f = CENTRE_X_I + BOX_WIDTH_I / 2 + 24
    part_list.append(f'<rect x="{left_f}" y="{top_i}" '
                     f'width="{right_f-left_f}" height="{bottom_i-top_i}" '
                     f'rx="14" fill="none" stroke="{colour_str}" '
                     'stroke-width="1.4" stroke-dasharray="8 5"/>')
    title_x_f, title_y_f = left_f - 12, (top_i + bottom_i) / 2
    part_list.append(f'<text x="{title_x_f}" y="{title_y_f}" '
                     f'transform="rotate(-90 {title_x_f} {title_y_f})" '
                     'text-anchor="middle" font-size="16" font-weight="700" '
                     f'fill="{colour_str}">{escape(title_str)}</text>')


def draw_returns(part_list: list, position_dict: dict) -> None:
    """Draw the return rails from the decisions back to step 5a.

    Inputs:
        part_list: the SVG parts drawn so far, extended in place.
        position_dict: the positions of step_positions.
    Outputs: none. Each rail enters the right edge of step 5a at its own
        height, and its label is written right of the rails.
    """
    top_5a_i, height_5a_i = position_dict["5a"][0], position_dict["5a"][1]
    right_f = CENTRE_X_I + BOX_WIDTH_I / 2
    for index_i, (source_id_str, rail_i, colour_str, dashed_b,
                  label_list) in enumerate(RETURN_LIST):
        start_y_f = (position_dict[source_id_str][0]
                     + position_dict[source_id_str][1] / 2)
        start_x_f = CENTRE_X_I + BOX_WIDTH_I / 2
        rail_x_i = RAIL_X_LIST[rail_i]
        end_y_f = top_5a_i + 12 + index_i * (height_5a_i - 24) / 3
        dash_str = ' stroke-dasharray="7 5"' if dashed_b else ""
        part_list.append(f'<polyline points="{start_x_f},{start_y_f} '
                         f'{rail_x_i},{start_y_f} {rail_x_i},{end_y_f} '
                         f'{right_f+4},{end_y_f}" fill="none" '
                         f'stroke="{colour_str}" stroke-width="1.6"'
                         f'{dash_str} marker-end="url(#a{colour_str[1:]})"/>')
        for line_index_i, line_str in enumerate(label_list):
            label_y_f = (start_y_f - (len(label_list)-1)*8
                         + line_index_i*16 + 4)
            part_list.append(
                f'<text x="{RAIL_X_LIST[-1]+16}" y="{label_y_f}"'
                f' font-size="13" fill="{colour_str}">{escape(line_str)}'
                '</text>')


def draw_legend(part_list: list) -> None:
    """Draw the legend at the top left.

    Inputs:
        part_list: the SVG parts drawn so far, extended in place.
    Outputs: none.
    """
    legend_x_i, legend_y_i = 40, 110
    part_list.append(f'<rect x="{legend_x_i-14}" y="{legend_y_i-30}" '
                     'width="190" height="300" rx="12" fill="#fafafa" '
                     'stroke="#999"/>')
    part_list.append(f'<text x="{legend_x_i}" y="{legend_y_i-8}" '
                     'font-size="15" font-weight="700">Legend</text>')
    for index_i, (kind_str, name_str) in enumerate(
            [("owner", "Owner"), ("impl", "Implementer"),
             ("rev", "Reviewer"), ("ci", "CI"), ("frozen", "Frozen state")]):
        fill_str, stroke_str, text_colour_str = COLOUR_DICT[kind_str]
        dash_str = ' stroke-dasharray="6 4"' if kind_str == "frozen" else ""
        part_list.append(f'<rect x="{legend_x_i}" '
                         f'y="{legend_y_i+10+index_i*42}" width="160" '
                         f'height="30" rx="8" fill="{fill_str}" '
                         f'stroke="{stroke_str}"{dash_str}/>')
        part_list.append(f'<text x="{legend_x_i+80}" '
                         f'y="{legend_y_i+30+index_i*42}" '
                         'text-anchor="middle" font-size="14" '
                         f'fill="{text_colour_str}">{name_str}</text>')
    part_list.append(f'<line x1="{legend_x_i}" y1="{legend_y_i+235}" '
                     f'x2="{legend_x_i+50}" y2="{legend_y_i+235}" '
                     'stroke="#b91c1c" stroke-width="1.6" '
                     'stroke-dasharray="7 5"/>')
    part_list.append(f'<text x="{legend_x_i+58}" y="{legend_y_i+239}" '
                     'font-size="13" fill="#b91c1c">back to the</text>')
    part_list.append(f'<text x="{legend_x_i+58}" y="{legend_y_i+255}" '
                     'font-size="13" fill="#b91c1c">implementer (5a)</text>')


def flow_svg() -> tuple:
    """Draw the whole flow.

    Inputs: none.
    Outputs: a tuple (SVG text, image height).
    """
    part_list = []
    position_dict, image_height_i = step_positions()
    draw_cluster(part_list, position_dict, "4", "6", "#1d4ed8",
                 "Implementer loop — no PR, no CI")
    draw_cluster(part_list, position_dict, "7", "10", "#15803d",
                 "Reviewer — the only one working on the branch")
    for step_id_str, *_ in STEP_LIST:
        draw_step(part_list, position_dict, step_id_str)
    step_id_list = [step_tuple[0] for step_tuple in STEP_LIST]
    for upper_id_str, lower_id_str in zip(step_id_list, step_id_list[1:]):
        upper_bottom_i = (position_dict[upper_id_str][0]
                          + position_dict[upper_id_str][1])
        lower_top_i = position_dict[lower_id_str][0]
        draw_arrow(part_list, CENTRE_X_I, upper_bottom_i, CENTRE_X_I,
                   lower_top_i - 2)
        if upper_id_str in DOWN_LABEL_DICT:
            part_list.append(
                f'<text x="{CENTRE_X_I+10}" '
                f'y="{(upper_bottom_i+lower_top_i)/2+5}" font-size="13" '
                f'fill="#333">{escape(DOWN_LABEL_DICT[upper_id_str])}</text>')
    draw_returns(part_list, position_dict)
    draw_legend(part_list)
    marker_str = "".join(
        f'<marker id="a{colour_str[1:]}" viewBox="0 0 10 10" refX="9" '
        'refY="5" markerWidth="8" markerHeight="8" '
        'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" '
        f'fill="{colour_str}"/></marker>'
        for colour_str in ["#444", "#1d4ed8", "#b91c1c"])
    svg_str = (f'<svg xmlns="http://www.w3.org/2000/svg" '
               f'width="{IMAGE_WIDTH_I}" height="{image_height_i}" '
               f'viewBox="0 0 {IMAGE_WIDTH_I} {image_height_i}" '
               'font-family="Helvetica, Arial, sans-serif">'
               f'<defs>{marker_str}</defs>'
               '<rect width="100%" height="100%" fill="#fff"/>'
               f'<text x="{IMAGE_WIDTH_I/2}" y="48" text-anchor="middle" '
               'font-size="24" font-weight="700">plot_tool — from feature '
               'or fix issue to merge into develop</text>'
               + "".join(part_list) + "</svg>")
    return svg_str, image_height_i


def main() -> None:
    """Write the SVG and print its size.

    Inputs: none.
    Outputs: none (writes OUTPUT_PATH_STR).
    """
    svg_str, image_height_i = flow_svg()
    with open(OUTPUT_PATH_STR, "w", encoding="utf-8") as svg_file:
        svg_file.write(svg_str)
    print(IMAGE_WIDTH_I, image_height_i)


if __name__ == "__main__":
    main()
