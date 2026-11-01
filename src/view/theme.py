"""Design tokens and style sheets of the interface, kept in one place.

Every color, radius, spacing and font size of the window chrome comes
from here, and the widgets get their style sheets from the functions of
this module (COR-00009: only the view uses it). The design follows one
principle: color belongs to the data. The chrome is a calm, cool grey
and white, and the only strong colors on screen are the curves, the
vertical markers and the tips. Active buttons (HLFR-00003) are shown in
dark ink with white text, which reads clearly against the light normal
buttons without competing with the curve colors.

Colors fixed by requirements are not defined here: the curve palette and
the reserved marker color stay in model/curve_colors.py (LLFR-00033,
LLFR-00083, LLFR-00144), and the plot widget keeps its dashed marker and
leader line styles (LLFR-00143, LLFR-00151).

Contents:
- color, radius, spacing and font tokens (``*_COLOR_STR``, ``*_I``,
  ``*_F``);
- ``application_style_sheet`` and ``apply_application_theme``: the
  style sheet of the whole application, set once on the QApplication;
- ``toggle_button_style_sheet``: the per-state style sheet of the top
  panel buttons (LLFR-00001, LLFR-00141);
- icon tokens: the colors of the button icons in each state and their
  sizes (LLFR-00158 to LLFR-00160), and the colors of the app icon
  (LLFR-00183);
- ``tab_style_sheet``: the tab bar and "+" button rules (LLFR-00106,
  LLFR-00107);
- ``MATPLOTLIB_STYLE_DICT``, ``apply_matplotlib_style`` and the
  annotation box dicts: the look of the plots;
- ``contrast_ratio_f``: the WCAG contrast ratio of two colors.
"""

# ----------------------------------------------------------------------
# Colors of the chrome
# ----------------------------------------------------------------------
# Window background: a cool, light grey on which the panels sit.
WINDOW_COLOR_STR = "#eceff2"
# Surfaces that hold content: signal list, search box, menus, dialogs.
SURFACE_COLOR_STR = "#ffffff"
# The well behind the plots of a tab; the selected tab has the same
# color, so it joins the page below it like a browser tab.
PLOT_WELL_COLOR_STR = "#f6f7f9"
# Main text, a dark slate ink, and muted text for secondary labels.
TEXT_COLOR_STR = "#24303b"
MUTED_TEXT_COLOR_STR = "#5f6c78"
# Hairlines between areas and the slightly stronger border of controls.
HAIRLINE_COLOR_STR = "#d5dbe1"
CONTROL_BORDER_COLOR_STR = "#c3cbd3"
# Rows of the signal list and items of the menus.
ROW_HOVER_COLOR_STR = "#f0f3f6"
ROW_SELECTED_COLOR_STR = "#e1e7ed"
# Keyboard focus of the search box and the signal list.
FOCUS_COLOR_STR = "#4b7aa8"
# The handle between the plot and signal list panels while hovered.
SPLITTER_HOVER_COLOR_STR = "#c9d1d9"

# ----------------------------------------------------------------------
# Buttons of the top panel (HLFR-00003)
# ----------------------------------------------------------------------
# LLFR-00001: dark ink background with white text while active; its
# contrast with the normal background is far above 3:1.
ACTIVE_COLOR_STR = "#2a3744"
ACTIVE_TEXT_COLOR_STR = "#ffffff"
# LLFR-00002, LLFR-00003: a light, near-white button while normal.
NORMAL_COLOR_STR = "#f6f7f9"
NORMAL_TEXT_COLOR_STR = TEXT_COLOR_STR
NORMAL_HOVER_COLOR_STR = "#ffffff"
NORMAL_PRESSED_COLOR_STR = "#e4e8ec"
BUTTON_BORDER_COLOR_STR = CONTROL_BORDER_COLOR_STR
# LLFR-00141: the disabled Undo button is paler than a normal button in
# background, text and border.
DISABLED_COLOR_STR = "#fbfcfd"
DISABLED_TEXT_COLOR_STR = "#b1bac3"
DISABLED_BORDER_COLOR_STR = "#dfe4e9"
BUTTON_RADIUS_I = 6
BUTTON_VERTICAL_PADDING_I = 6
BUTTON_HORIZONTAL_PADDING_I = 12
# Position of a button in a segmented group (the plot tools, which are
# exclusive, HLFR-00032, are drawn joined): single, first, middle, last.
SEGMENT_SINGLE_STR = "single"
SEGMENT_FIRST_STR = "first"
SEGMENT_MIDDLE_STR = "middle"
SEGMENT_LAST_STR = "last"

# ----------------------------------------------------------------------
# Icons of the top panel buttons (LLFR-00158 to LLFR-00160)
# ----------------------------------------------------------------------
# LLFR-00158: the buttons are squares that show only their icon.
ICON_BUTTON_SIZE_I = 32
ICON_SIZE_I = 20
# LLFR-00160: the icon is drawn in the button's text color in each
# state: dark ink on the light normal button, white on the dark active
# button, and a paler grey on the disabled button that still keeps a
# contrast of at least 3:1 with the disabled background.
ICON_COLOR_STR = NORMAL_TEXT_COLOR_STR
ICON_ACTIVE_COLOR_STR = ACTIVE_TEXT_COLOR_STR
ICON_DISABLED_COLOR_STR = "#87929d"
# LLFR-00160: smallest contrast between an icon and its background.
MINIMUM_ICON_CONTRAST_F = 3.0

# ----------------------------------------------------------------------
# App icon (LLFR-00183)
# ----------------------------------------------------------------------
# LLFR-00183: a light rounded square, lit from the top, with dark axes;
# the curves use the palette blue and red of LLFR-00144 (they are read
# from model/curve_colors.py by view.icons).
APP_ICON_TOP_COLOR_STR = "#ffffff"
APP_ICON_BOTTOM_COLOR_STR = "#e6ebf0"
APP_ICON_BORDER_COLOR_STR = CONTROL_BORDER_COLOR_STR
APP_ICON_AXIS_COLOR_STR = ACTIVE_COLOR_STR

# ----------------------------------------------------------------------
# Spacing (an 8 px grid, with 4 px half steps)
# ----------------------------------------------------------------------
WINDOW_MARGIN_I = 12
WINDOW_TOP_MARGIN_I = 10
PANEL_SPACING_I = 10
TOOLBAR_BUTTON_GAP_I = 4
TOOLBAR_GROUP_GAP_I = 16
SIGNAL_PANEL_SPACING_I = 8
SPLITTER_HANDLE_WIDTH_I = 8
PLOT_SPACING_I = 6
CONTROL_RADIUS_I = 6
MENU_RADIUS_I = 6
TOOLTIP_RADIUS_I = 4

# ----------------------------------------------------------------------
# Tabs of the plot panel (LLFR-00106, LLFR-00107)
# ----------------------------------------------------------------------
# LLFR-00107: the look shared by the unselected tabs and the "+" button.
TAB_BACKGROUND_COLOR_STR = "#e2e6ea"
TAB_HOVER_COLOR_STR = "#d8dde2"
TAB_SELECTED_COLOR_STR = PLOT_WELL_COLOR_STR
TAB_TEXT_COLOR_STR = MUTED_TEXT_COLOR_STR
TAB_SELECTED_TEXT_COLOR_STR = TEXT_COLOR_STR
TAB_BORDER_COLOR_STR = CONTROL_BORDER_COLOR_STR
# The selected tab is marked by an ink line along its top edge.
TAB_SELECTED_MARK_COLOR_STR = ACTIVE_COLOR_STR
TAB_SELECTED_MARK_WIDTH_I = 2
TAB_BORDER_WIDTH_I = 1
TAB_CORNER_RADIUS_I = 6
TAB_MINIMUM_TEXT_WIDTH_I = 48
TAB_HORIZONTAL_PADDING_I = 14
TAB_VERTICAL_PADDING_I = 5
TAB_SPACING_I = 3
ADD_BUTTON_WIDTH_I = 30

# ----------------------------------------------------------------------
# Plots (matplotlib)
# ----------------------------------------------------------------------
PLOT_BACKGROUND_COLOR_STR = "#ffffff"
PLOT_SPINE_COLOR_STR = "#b8c1ca"
PLOT_TICK_COLOR_STR = "#5f6c78"
PLOT_GRID_COLOR_STR = "#e3e7ec"
PLOT_GRID_LINE_WIDTH_F = 0.8
PLOT_TICK_FONT_SIZE_F = 8.5
PLOT_LABEL_FONT_SIZE_F = 9.0
PLOT_TIP_FONT_SIZE_F = 8.5
# The system interface fonts first, so the plots match the chrome on
# each platform; DejaVu Sans ships with matplotlib, so it always works.
PLOT_FONT_FAMILY_LIST = ["Segoe UI", "Helvetica Neue", "Helvetica",
                         "Arial", "Noto Sans", "DejaVu Sans"]
# Text color of a tip whose curve is unknown.
DEFAULT_TIP_COLOR_STR = TEXT_COLOR_STR
TIP_TEXT_COLOR_STR = TEXT_COLOR_STR

# rcParams applied to every figure (apply_matplotlib_style).
MATPLOTLIB_STYLE_DICT = {
    "figure.facecolor": PLOT_BACKGROUND_COLOR_STR,
    "axes.facecolor": PLOT_BACKGROUND_COLOR_STR,
    "axes.edgecolor": PLOT_SPINE_COLOR_STR,
    "axes.linewidth": 0.8,
    "axes.labelcolor": PLOT_TICK_COLOR_STR,
    "axes.labelsize": PLOT_LABEL_FONT_SIZE_F,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": False,
    "grid.color": PLOT_GRID_COLOR_STR,
    "grid.linewidth": PLOT_GRID_LINE_WIDTH_F,
    "grid.linestyle": "-",
    "xtick.color": PLOT_SPINE_COLOR_STR,
    "ytick.color": PLOT_SPINE_COLOR_STR,
    "xtick.labelcolor": PLOT_TICK_COLOR_STR,
    "ytick.labelcolor": PLOT_TICK_COLOR_STR,
    "xtick.labelsize": PLOT_TICK_FONT_SIZE_F,
    "ytick.labelsize": PLOT_TICK_FONT_SIZE_F,
    "xtick.major.size": 3.0,
    "ytick.major.size": 3.0,
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    "font.family": "sans-serif",
    "font.sans-serif": PLOT_FONT_FAMILY_LIST,
    "legend.frameon": False,
    "legend.handlelength": 1.6,
    "legend.handletextpad": 0.5,
    "legend.columnspacing": 1.6,
    "savefig.facecolor": PLOT_BACKGROUND_COLOR_STR,
}

# LLFR-00042: the hover tip, a white rounded box with a hairline border.
HOVER_TIP_BOX_DICT = {"boxstyle": "round,pad=0.45,rounding_size=0.35",
                      "facecolor": PLOT_BACKGROUND_COLOR_STR,
                      "edgecolor": PLOT_SPINE_COLOR_STR,
                      "linewidth": 0.8, "alpha": 0.96}
# LLFR-00045: a pinned tip has the same box with a border in the curve's
# color (set by the plot widget).
PINNED_TIP_BOX_DICT = {"boxstyle": "round,pad=0.45,rounding_size=0.35",
                       "facecolor": PLOT_BACKGROUND_COLOR_STR,
                       "linewidth": 1.0, "alpha": 0.96}
# LLFR-00084, LLFR-00092: the marker name and time sit on a soft white
# rounded patch so they stay readable over the curves.
MARKER_TEXT_BOX_DICT = {"boxstyle": "round,pad=0.2,rounding_size=0.25",
                        "facecolor": PLOT_BACKGROUND_COLOR_STR,
                        "edgecolor": "none", "alpha": 0.92}


def segment_corner_rule(segment_str: str) -> str:
    """Return the border and corner declarations of a button segment.

    Inputs:
        segment_str: SEGMENT_SINGLE_STR, SEGMENT_FIRST_STR,
            SEGMENT_MIDDLE_STR or SEGMENT_LAST_STR.
    Outputs: Qt style sheet declarations for the corner radii and the
        left border; joined segments share one border line.
    """
    # LLFR-00001: the plot tool buttons form one joined group.
    radius_str = f"{BUTTON_RADIUS_I}px"
    if segment_str == SEGMENT_FIRST_STR:
        return (f"border-top-left-radius: {radius_str}; "
                f"border-bottom-left-radius: {radius_str}; "
                "border-top-right-radius: 0px; "
                "border-bottom-right-radius: 0px;")
    if segment_str == SEGMENT_MIDDLE_STR:
        return "border-radius: 0px; border-left-width: 0px;"
    if segment_str == SEGMENT_LAST_STR:
        return (f"border-top-right-radius: {radius_str}; "
                f"border-bottom-right-radius: {radius_str}; "
                "border-top-left-radius: 0px; "
                "border-bottom-left-radius: 0px; "
                "border-left-width: 0px;")
    return f"border-radius: {radius_str};"


def toggle_button_style_sheet(object_name_str: str, active_b: bool,
                              segment_str: str = SEGMENT_SINGLE_STR,
                              disabled_rule_b: bool = False,
                              icon_only_b: bool = False) -> str:
    """Return the style sheet of a top panel button in one state.

    Inputs:
        object_name_str: the button's objectName; the rules are scoped
            to it so they never leak to other widgets.
        active_b: True for the active look (LLFR-00001), False for the
            normal look (LLFR-00002, LLFR-00003).
        segment_str: the button's place in a joined group.
        disabled_rule_b: True to add the paler disabled rule
            (LLFR-00141).
        icon_only_b: True for a square button that shows only its icon
            (LLFR-00158); the icon is centred with no padding.
    Outputs: a Qt style sheet. The same border and padding are used in
        every state, so the button keeps its size when it changes color.
        The hover color of an active button is the active color itself,
        so the active state always shows the same color.
    """
    # LLFR-00001, LLFR-00002, LLFR-00003: the color follows the state.
    selector_str = f"QPushButton#{object_name_str}"
    if active_b:
        background_str = ACTIVE_COLOR_STR
        text_str = ACTIVE_TEXT_COLOR_STR
        border_str = ACTIVE_COLOR_STR
        hover_str = ACTIVE_COLOR_STR
        pressed_str = ACTIVE_COLOR_STR
    else:
        background_str = NORMAL_COLOR_STR
        text_str = NORMAL_TEXT_COLOR_STR
        border_str = BUTTON_BORDER_COLOR_STR
        hover_str = NORMAL_HOVER_COLOR_STR
        pressed_str = NORMAL_PRESSED_COLOR_STR
    # LLFR-00158: an icon button has no padding; its fixed square size
    # (ICON_BUTTON_SIZE_I) frames the icon.
    if icon_only_b:
        padding_str = "padding: 0px;"
    else:
        padding_str = (f"padding: {BUTTON_VERTICAL_PADDING_I}px "
                       f"{BUTTON_HORIZONTAL_PADDING_I}px;")
    rule_list = [
        f"{selector_str} {{ background-color: {background_str}; "
        f"color: {text_str}; border: 1px solid {border_str}; "
        f"{segment_corner_rule(segment_str)} {padding_str} }}",
        f"{selector_str}:hover {{ background-color: {hover_str}; }}",
        f"{selector_str}:pressed {{ background-color: {pressed_str}; }}",
    ]
    if disabled_rule_b:
        # LLFR-00141: this rule comes last, so it wins while disabled.
        rule_list.append(
            f"{selector_str}:disabled {{ "
            f"background-color: {DISABLED_COLOR_STR}; "
            f"color: {DISABLED_TEXT_COLOR_STR}; "
            f"border: 1px solid {DISABLED_BORDER_COLOR_STR}; "
            f"{segment_corner_rule(segment_str)} }}")
    return "\n".join(rule_list)


# LLFR-00107: one declaration block for background, border and corners,
# used by both the unselected tab rule and the "+" button rule.
SHARED_TAB_SHAPE_STR = (
    f"background: {TAB_BACKGROUND_COLOR_STR}; "
    f"color: {TAB_TEXT_COLOR_STR}; "
    f"border: {TAB_BORDER_WIDTH_I}px solid {TAB_BORDER_COLOR_STR}; "
    f"border-top-left-radius: {TAB_CORNER_RADIUS_I}px; "
    f"border-top-right-radius: {TAB_CORNER_RADIUS_I}px; "
    "border-bottom-left-radius: 0px; "
    "border-bottom-right-radius: 0px;")


def tab_style_sheet(tab_widget_name_str: str, tab_bar_name_str: str,
                    add_button_name_str: str) -> str:
    """Return the style sheet of the plot tab widget.

    Inputs:
        tab_widget_name_str: objectName of the QTabWidget.
        tab_bar_name_str: objectName of its QTabBar.
        add_button_name_str: objectName of the "+" QToolButton.
    Outputs: a Qt style sheet that aligns the tab bar to the left
        (LLFR-00106) and gives the unselected tabs and the "+" button the
        same shape block SHARED_TAB_SHAPE_STR (LLFR-00107).
    """
    # LLFR-00106: tabs start at the left edge on every platform (macOS
    # centres them by default).
    tab_widget_str = f"QTabWidget#{tab_widget_name_str}"
    tab_str = f"QTabBar#{tab_bar_name_str}::tab"
    button_str = f"QToolButton#{add_button_name_str}"
    rule_list = [
        f"{tab_widget_str}::tab-bar {{ alignment: left; left: 0px; }}",
        f"{tab_widget_str}::pane {{ background: {PLOT_WELL_COLOR_STR}; "
        f"border: {TAB_BORDER_WIDTH_I}px solid {TAB_BORDER_COLOR_STR}; "
        f"top: -{TAB_BORDER_WIDTH_I}px; }}",
        # LLFR-00107: size of every tab; the "+" gets the tab height
        # from its geometry (PlotTabWidget.reposition_add_button).
        f"{tab_str} {{ {SHARED_TAB_SHAPE_STR} "
        f"min-width: {TAB_MINIMUM_TEXT_WIDTH_I}px; "
        f"padding: {TAB_VERTICAL_PADDING_I}px "
        f"{TAB_HORIZONTAL_PADDING_I}px; "
        f"margin: 0px {TAB_SPACING_I}px 0px 0px; }}",
        f"{tab_str}:!selected {{ {SHARED_TAB_SHAPE_STR} }}",
        f"{tab_str}:!selected:hover {{ background: {TAB_HOVER_COLOR_STR}; }}",
        # The selected tab joins the plot well below it and carries an
        # ink line on its top edge.
        f"{tab_str}:selected {{ background: {TAB_SELECTED_COLOR_STR}; "
        f"color: {TAB_SELECTED_TEXT_COLOR_STR}; "
        f"border-top: {TAB_SELECTED_MARK_WIDTH_I}px solid "
        f"{TAB_SELECTED_MARK_COLOR_STR}; "
        f"border-bottom-color: {TAB_SELECTED_COLOR_STR}; }}",
        f"{button_str} {{ {SHARED_TAB_SHAPE_STR} padding: 0px; "
        "margin: 0px; }",
        f"{button_str}:hover {{ background: {TAB_HOVER_COLOR_STR}; "
        f"color: {TEXT_COLOR_STR}; }}",
        f"{button_str}:pressed {{ background: {TAB_SELECTED_COLOR_STR}; }}",
    ]
    return "\n".join(rule_list)


def application_style_sheet() -> str:
    """Return the style sheet set once on the whole application.

    Inputs: none.
    Outputs: a Qt style sheet for the window background, the signal list
        panel, the search box, the splitter handle, menus, tooltips,
        message boxes and dialogs. The top panel buttons and the tabs
        add their own scoped rules (toggle_button_style_sheet,
        tab_style_sheet).
    """
    # LLFR-00058: the three panels sit on the window background.
    # LLFR-00094, LLFR-00097: the signal list, its search box and the
    # no-match text.
    radius_str = f"{CONTROL_RADIUS_I}px"
    rule_list = [
        f"QMainWindow, QDialog, QMessageBox {{ "
        f"background: {WINDOW_COLOR_STR}; color: {TEXT_COLOR_STR}; }}",
        f"QLabel {{ color: {TEXT_COLOR_STR}; }}",
        # Signal list panel.
        f"QLabel#signal_list_title {{ color: {TEXT_COLOR_STR}; "
        "font-weight: 600; padding: 6px 2px 0px 2px; }",
        f"QListWidget#signal_list_widget {{ background: "
        f"{SURFACE_COLOR_STR}; color: {TEXT_COLOR_STR}; "
        f"border: 1px solid {HAIRLINE_COLOR_STR}; border-radius: "
        f"{radius_str}; padding: 4px; outline: none; }}",
        f"QListWidget#signal_list_widget:focus {{ border-color: "
        f"{FOCUS_COLOR_STR}; }}",
        "QListWidget#signal_list_widget::item { padding: 4px 8px; "
        "border-radius: 4px; border: none; }",
        f"QListWidget#signal_list_widget::item:hover {{ background: "
        f"{ROW_HOVER_COLOR_STR}; }}",
        f"QListWidget#signal_list_widget::item:selected {{ background: "
        f"{ROW_SELECTED_COLOR_STR}; color: {TEXT_COLOR_STR}; }}",
        f"QLabel#no_match_label {{ color: {MUTED_TEXT_COLOR_STR}; "
        "padding-top: 16px; }",
        f"QLineEdit {{ background: {SURFACE_COLOR_STR}; "
        f"color: {TEXT_COLOR_STR}; border: 1px solid "
        f"{CONTROL_BORDER_COLOR_STR}; border-radius: {radius_str}; "
        f"padding: 5px 8px; selection-background-color: "
        f"{ROW_SELECTED_COLOR_STR}; selection-color: {TEXT_COLOR_STR}; }}",
        f"QLineEdit:focus {{ border-color: {FOCUS_COLOR_STR}; }}",
        # Splitter between the plot and signal list panels (LLFR-00073).
        "QSplitter::handle { background: transparent; }",
        f"QSplitter::handle:hover {{ background: "
        f"{SPLITTER_HOVER_COLOR_STR}; border-radius: 2px; }}",
        # Menus: tab, curve, plot, marker, tip and Export menus.
        f"QMenu {{ background: {SURFACE_COLOR_STR}; color: "
        f"{TEXT_COLOR_STR}; border: 1px solid {HAIRLINE_COLOR_STR}; "
        "padding: 4px; }",
        "QMenu::item { padding: 5px 24px 5px 14px; border-radius: 4px; }",
        f"QMenu::item:selected {{ background: {ROW_SELECTED_COLOR_STR}; "
        f"color: {TEXT_COLOR_STR}; }}",
        f"QMenu::item:disabled {{ color: {DISABLED_TEXT_COLOR_STR}; }}",
        f"QMenu::separator {{ height: 1px; background: "
        f"{HAIRLINE_COLOR_STR}; margin: 4px 6px; }}",
        # LLFR-00181: the name of a top panel button shown on hover.
        f"QToolTip {{ background: {SURFACE_COLOR_STR}; color: "
        f"{TEXT_COLOR_STR}; border: 1px solid {CONTROL_BORDER_COLOR_STR}; "
        f"border-radius: {TOOLTIP_RADIUS_I}px; padding: 3px 7px; }}",
        # Buttons of message boxes and dialogs (the top panel buttons
        # have their own scoped rules, which take precedence).
        f"QDialog QPushButton, QMessageBox QPushButton {{ "
        f"background: {NORMAL_COLOR_STR}; color: {TEXT_COLOR_STR}; "
        f"border: 1px solid {CONTROL_BORDER_COLOR_STR}; "
        f"border-radius: {radius_str}; padding: 5px 16px; "
        "min-width: 64px; }",
        f"QDialog QPushButton:hover, QMessageBox QPushButton:hover {{ "
        f"background: {NORMAL_HOVER_COLOR_STR}; }}",
        f"QDialog QPushButton:pressed, QMessageBox QPushButton:pressed {{ "
        f"background: {NORMAL_PRESSED_COLOR_STR}; }}",
        f"QDialog QPushButton:default, QMessageBox QPushButton:default {{ "
        f"border-color: {ACTIVE_COLOR_STR}; }}",
        f"QDialog QPushButton:focus, QMessageBox QPushButton:focus {{ "
        f"border-color: {FOCUS_COLOR_STR}; }}",
    ]
    return "\n".join(rule_list)


def apply_application_theme(application) -> None:
    """Set the application style sheet once.

    Inputs:
        application: the QApplication, or None (then nothing happens).
    Outputs: none. Setting the same style sheet again is skipped, so
        creating several windows does not restyle every widget again.
    """
    # LLFR-00058: one style sheet for the whole application.
    if application is None:
        return
    style_sheet_str = application_style_sheet()
    if application.styleSheet() != style_sheet_str:
        application.setStyleSheet(style_sheet_str)


def apply_matplotlib_style() -> None:
    """Apply the plot look to matplotlib's defaults.

    Inputs: none.
    Outputs: none. New figures and artists use MATPLOTLIB_STYLE_DICT
        (light spines, muted ticks, light grid, interface fonts). Curve
        colors, marker colors and line styles are always given
        explicitly by the plot widget, so they are not affected.
    """
    # LLFR-00068: the time axis and its labels get the theme's look.
    import matplotlib
    # LLFR-00068: the plots are always drawn by the QtAgg backend, so
    # matplotlib never looks for other backends, and the standalone
    # build (build_executable.py) bundles only that one (issue #67).
    matplotlib.use("QtAgg")
    matplotlib.rcParams.update(MATPLOTLIB_STYLE_DICT)


def relative_luminance_f(color_str: str) -> float:
    """Return the WCAG relative luminance of a "#rrggbb" color.

    Inputs:
        color_str: the color as "#rrggbb".
    Outputs: the luminance, from 0.0 (black) to 1.0 (white).
    """
    # LLFR-00001: used to check that the active color stands out.
    channel_list = []
    for start_i in (1, 3, 5):
        channel_f = int(color_str[start_i:start_i + 2], 16) / 255.0
        if channel_f <= 0.03928:
            channel_list.append(channel_f / 12.92)
        else:
            channel_list.append(((channel_f + 0.055) / 1.055) ** 2.4)
    return (0.2126 * channel_list[0] + 0.7152 * channel_list[1]
            + 0.0722 * channel_list[2])


def contrast_ratio_f(first_color_str: str, second_color_str: str) -> float:
    """Return the WCAG contrast ratio of two "#rrggbb" colors.

    Inputs:
        first_color_str: one color.
        second_color_str: the other color.
    Outputs: the ratio, from 1.0 (same luminance) to 21.0.
    """
    # LLFR-00001: active and normal buttons must be told apart clearly.
    luminance_list = sorted([relative_luminance_f(first_color_str),
                             relative_luminance_f(second_color_str)])
    return (luminance_list[1] + 0.05) / (luminance_list[0] + 0.05)
