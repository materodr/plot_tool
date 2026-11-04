"""Signal list panel: shows the signals of the open data files.

Below the list there is a search box (HLFR-00033) whose text is passed
to the signal list controller, which decides which names are shown and
gives the text shown when nothing matches (the view does not import the
model, COR-00009).

The list is made of groups, one per open data file, in the order of the
file numbers (LLFR-00934). Each group starts with the file name row of
its file (LLFR-00362), ``file<N>_<file name>`` in bold, followed by the
shown signals of that file and its synthetic signals (LLFR-00935,
LLFR-00242), or by the text "No matching signals" when none of them
matches the search (LLFR-00097, LLFR-00641). A file name row is an item
of the list that is not a signal (LLFR-00642): it can't be selected,
also not by a Shift + click range (LLFR-00643, LLFR-00644), dragged
(LLFR-00645), plotted with a double-click or Enter (LLFR-00646), and a
right-click on it opens the file menu, "Close file" and "Close all
files" (LLFR-00647, LLFR-00919), instead of the signal menu. A file name
row that is too wide is shortened in the middle with "..." and has the
whole text as its tip (LLFR-00648, LLFR-00649). The "No matching
signals" row is not a signal either.

A right-click on a signal name opens the signal menu (LLFR-00239):
"Create synthetic signal" with the operations given by the controller,
in groups (LLFR-00268), disabled for an FFT signal (LLFR-00251); "Copy
name" (LLFR-00277); and, for a synthetic signal, "Copy equation"
(LLFR-00278), "Rename" (LLFR-00265) and "Delete signal" (LLFR-00254).
Synthetic signals are shown in italics (LLFR-00242) and the time signals
in green, also while selected (LLFR-00332). A menu is shown once the
right-click has been handled, and its request is emitted after the menu
is closed, so a request may change the list safely.

Several signals can be selected (HLFR-00063): a click selects one, a
click with the Data tip key (Cmd on macOS, which Qt reports as the
Control modifier, Ctrl elsewhere) toggles one and a click with Shift
selects a range, as Qt's extended selection does (LLFR-00290). The
Enter key plots the selection in one new plot (LLFR-00295), and a drag
from a selected signal carries every selected name, in list order
(LLFR-00297), as a JSON list in SIGNAL_LIST_MIME_TYPE_STR.
"""

import json

from PyQt6.QtCore import (
    QByteArray, QItemSelectionModel, QMimeData, QPoint, Qt, QTimer,
    pyqtSignal)
from PyQt6.QtGui import QBrush, QColor, QFontMetrics, QPalette
from PyQt6.QtWidgets import (
    QAbstractItemView, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMenu, QStyledItemDelegate, QVBoxLayout, QWidget)

from view import theme
from view.elided_text import is_elided, middle_elided_text

# LLFR-00021: MIME type of a dragged signal name. The plot widget
# accepts drops of this type, so the literal must stay the same there.
SIGNAL_MIME_TYPE_STR = "application/x-plot-tool-signal"
# LLFR-00297: MIME type of the dragged names, as a JSON list in list
# order; the plot widget uses the same literal.
SIGNAL_LIST_MIME_TYPE_STR = "application/x-plot-tool-signal-list"
# LLFR-00295: the keys that plot the selection (Return and Enter act the
# same).
PLOT_SELECTION_KEY_TUPLE = (Qt.Key.Key_Return, Qt.Key.Key_Enter)
PLAIN_TEXT_MIME_TYPE_STR = "text/plain"
TITLE_TEXT_STR = "Signals"
TEXT_ENCODING_STR = "utf-8"
# LLFR-00094: hint shown in the empty search box.
SEARCH_PLACEHOLDER_TEXT_STR = "Search signals"
# LLFR-00239, LLFR-00254, LLFR-00265, LLFR-00277, LLFR-00278: the
# options of the signal menu.
CREATE_SYNTHETIC_TEXT_STR = "Create synthetic signal"
COPY_NAME_TEXT_STR = "Copy name"
COPY_EQUATION_TEXT_STR = "Copy equation"
RENAME_SIGNAL_TEXT_STR = "Rename"
DELETE_SIGNAL_TEXT_STR = "Delete signal"
# LLFR-00919: the options of the file menu, in this order.
CLOSE_FILE_TEXT_STR = "Close file"
CLOSE_ALL_FILES_TEXT_STR = "Close all files"
# LLFR-00362, LLFR-00642, LLFR-00097: the kind of each row of the list,
# kept in the item's data, and the number of the file of a file row.
ROW_KIND_ROLE_I = Qt.ItemDataRole.UserRole.value
FILE_NUMBER_ROLE_I = ROW_KIND_ROLE_I + 1
SIGNAL_ROW_STR = "signal"
FILE_ROW_STR = "file"
NO_MATCH_ROW_STR = "no_match"
# LLFR-00648: the room the text of a row leaves on its sides: the
# padding of the theme ("padding: 4px 8px") and the text margin of the
# style, on the left and on the right.
ROW_TEXT_MARGIN_I = 24


def row_kind(item) -> str:
    """Return what a row of the signal list is.

    Inputs:
        item: a QListWidgetItem of the signal list, or None.
    Outputs: SIGNAL_ROW_STR, FILE_ROW_STR or NO_MATCH_ROW_STR; "" for
        None.
    """
    # LLFR-00642: a file name row and the no-match row are not signals.
    if item is None:
        return ""
    kind_str = item.data(ROW_KIND_ROLE_I)
    if kind_str is None:
        return SIGNAL_ROW_STR
    return str(kind_str)


def is_signal_row(item) -> bool:
    """Tell whether a row of the signal list is a signal.

    Inputs:
        item: a QListWidgetItem, or None.
    Outputs: True for a signal row.
    """
    # LLFR-00642, LLFR-00643, LLFR-00645, LLFR-00646.
    return row_kind(item) == SIGNAL_ROW_STR


def file_row_shown_text(whole_text_str: str, row_width_i: int,
                        font) -> str:
    """Return the text a file name row shows in a given width.

    Inputs:
        whole_text_str: the whole text of the row, ``file<N>_<name>``.
        row_width_i: the width of the row, in pixels.
        font: the QFont of the row (bold).
    Outputs: the whole text when it fits, otherwise the text shortened
        in the middle with "..." (LLFR-00648).
    """
    # LLFR-00648: "..." in the middle when the text does not fit.
    font_metrics = QFontMetrics(font)
    return middle_elided_text(str(whole_text_str),
                              max(0, int(row_width_i) - ROW_TEXT_MARGIN_I),
                              font_metrics.horizontalAdvance)


class SignalItemDelegate(QStyledItemDelegate):
    """Draws each row of the signal list.

    Qt draws the name of a selected row in the palette's highlighted
    text color, which would hide the green of the time signal. This
    delegate gives the highlighted text the color of the row's name.
    It also shortens the text of a file name row in the middle
    (LLFR-00648).

    Inputs:
        parent: the list widget.
    Outputs: the delegate.
    """

    def initStyleOption(self, option, index) -> None:
        """Fill the drawing options of one row.

        Inputs:
            option: the QStyleOptionViewItem to fill.
            index: the model index of the row.
        Outputs: none. The highlighted text color becomes the text
            color of the row; a file name row gets its shortened text.
        """
        super().initStyleOption(option, index)
        # LLFR-00332: a selected row keeps the color of its name.
        palette = QPalette(option.palette)
        for group in (QPalette.ColorGroup.Active,
                      QPalette.ColorGroup.Inactive,
                      QPalette.ColorGroup.Disabled):
            palette.setBrush(group, QPalette.ColorRole.HighlightedText,
                             palette.brush(group, QPalette.ColorRole.Text))
        option.palette = palette
        # LLFR-00648: a file name row that is too wide is shortened in
        # the middle, so that its number and its extension stay seen.
        if index.data(ROW_KIND_ROLE_I) == FILE_ROW_STR:
            option.text = file_row_shown_text(
                str(index.data(Qt.ItemDataRole.DisplayRole) or ""),
                option.rect.width(), option.font)
            option.textElideMode = Qt.TextElideMode.ElideNone


class SignalListWidget(QListWidget):
    """List of signal names that can be dragged but not reordered.

    Inputs:
        parent: optional parent widget.
    Attributes:
        pressed_item: the signal item under the last left press, or None
            (also for a press on a row that is not a signal).
        pressed_item_was_selected_b: True when that item was already
            selected before the press (LLFR-00298).
    Signals:
        plot_selection_requested(): the Enter key was pressed while the
            list has the keyboard focus (LLFR-00295).
    """

    plot_selection_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        """Create a multi-selection, drag-only list.

        Inputs:
            parent: optional parent widget.
        Outputs: none.
        """
        super().__init__(parent)
        # LLFR-00290: click, Data tip key + click and Shift + click, as
        # in Qt's extended selection; LLFR-00291: every selected signal
        # is highlighted.
        self.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection)
        # LLFR-00298: what the last left press was on.
        self.pressed_item = None
        self.pressed_item_was_selected_b = False
        # LLFR-00021: names can be dragged out, never dropped in or
        # reordered.
        self.setDragEnabled(True)
        self.setAcceptDrops(False)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        # LLFR-00021, LLFR-00154: a drag only copies the name, also with
        # Shift or Cmd held, so that Qt never removes the dragged row.
        self.setDefaultDropAction(Qt.DropAction.CopyAction)
        # LLFR-00332: the names keep their colors while selected;
        # LLFR-00648: file name rows are shortened in the middle.
        self.setItemDelegate(SignalItemDelegate(self))

    def row_items(self, kind_str: str = "") -> list:
        """Return the rows of the list, from top to bottom.

        Inputs:
            kind_str: SIGNAL_ROW_STR, FILE_ROW_STR or NO_MATCH_ROW_STR to
                keep only the rows of that kind; "" keeps every row.
        Outputs: a list of QListWidgetItem.
        """
        # LLFR-00934, LLFR-00935: the rows in the order of the list.
        item_list = [self.item(row_i) for row_i in range(self.count())]
        if not kind_str:
            return item_list
        return [item for item in item_list if row_kind(item) == kind_str]

    def refresh_file_row_tips(self) -> None:
        """Give each shortened file name row its whole text as a tip.

        Inputs: none.
        Outputs: none. A file name row that fits has no tip.
        """
        # LLFR-00649: the whole text in a tip while it is shortened.
        row_width_i = self.viewport().width()
        for item in self.row_items(FILE_ROW_STR):
            whole_text_str = item.text()
            shown_text_str = file_row_shown_text(whole_text_str,
                                                 row_width_i, item.font())
            if is_elided(shown_text_str, whole_text_str):
                item.setToolTip(whole_text_str)
            else:
                item.setToolTip("")

    def file_row_text(self, item) -> str:
        """Return the text a file name row shows at the list's width.

        Inputs:
            item: a file name row of this list.
        Outputs: the whole text, or the text shortened in the middle
            (LLFR-00648), as the delegate draws it.
        """
        # LLFR-00648: the same shortening as SignalItemDelegate.
        return file_row_shown_text(item.text(), self.viewport().width(),
                                   item.font())

    def resizeEvent(self, event) -> None:
        """Shorten the file name rows again when the list is resized.

        Inputs:
            event: the QResizeEvent.
        Outputs: none.
        """
        # LLFR-00648, LLFR-00649: the shortening and the tips follow the
        # width of the panel.
        super().resizeEvent(event)
        self.refresh_file_row_tips()

    def supportedDropActions(self):
        """Return the drop actions a drag from this list may end with.

        Inputs: none.
        Outputs: Qt.DropAction.CopyAction only.
        """
        # LLFR-00021, LLFR-00154: never a move, which would remove the
        # row from the list.
        return Qt.DropAction.CopyAction

    def mousePressEvent(self, event) -> None:
        """Remember what a left press is on, then select as Qt does.

        Inputs:
            event: the QMouseEvent.
        Outputs: none.
        """
        # LLFR-00298: whether the pressed signal was selected before the
        # press decides what a drag that starts here carries.
        clicked_item = self.itemAt(event.position().toPoint())
        if clicked_item is not None and not is_signal_row(clicked_item):
            # LLFR-00643, LLFR-00644, LLFR-00645: a press on a file name
            # row (or the no-match row) selects nothing, changes nothing
            # in the selection and starts no drag.
            if event.button() == Qt.MouseButton.LeftButton:
                self.pressed_item = None
                self.pressed_item_was_selected_b = False
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self.pressed_item = clicked_item
            self.pressed_item_was_selected_b = (
                clicked_item is not None and clicked_item.isSelected())
        # LLFR-00290: Qt's extended selection handles the modifiers;
        # the rows that are not signals are not selectable either, so
        # no Shift range selects them (LLFR-00644).
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        """Ignore a double-click on a row that is not a signal.

        Inputs:
            event: the QMouseEvent.
        Outputs: none.
        """
        # LLFR-00646: a double-click on a file name row plots nothing
        # and selects nothing.
        clicked_item = self.itemAt(event.position().toPoint())
        if clicked_item is not None and not is_signal_row(clicked_item):
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def select_only(self, item) -> None:
        """Select one item and deselect every other one.

        Inputs:
            item: a QListWidgetItem of this list.
        Outputs: none. The item also becomes the current item, the
            start of the next Shift + click range (LLFR-00290).
        """
        # LLFR-00293, LLFR-00298: only that signal is selected.
        self.clearSelection()
        self.setCurrentItem(item)
        item.setSelected(True)

    def drag_selection_check(self) -> None:
        """Select only the pressed signal when it was not selected.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00298: a drag that starts on a signal that was not
        # selected (also with the Data tip key held, which Qt would add
        # to the selection) drags that signal alone.
        pressed_item = self.pressed_item
        if (pressed_item is not None
                and not self.pressed_item_was_selected_b
                and self.row(pressed_item) >= 0):
            self.select_only(pressed_item)

    def startDrag(self, supported_actions) -> None:
        """Start dragging the selected signal names, as a copy only.

        Inputs:
            supported_actions: the Qt.DropAction flags Qt proposes; they
                are replaced by CopyAction.
        Outputs: none.
        """
        # LLFR-00645: a drag from a file name row drags nothing.
        if self.pressed_item is None:
            return
        # LLFR-00297, LLFR-00298: drag the selection, or the pressed
        # signal alone when it was not selected.
        self.drag_selection_check()
        # LLFR-00021, LLFR-00154: with Shift (or Cmd on macOS) held, Qt
        # would make the drop a move and then delete the dragged row;
        # offering only a copy keeps the signal list unchanged.
        super().startDrag(Qt.DropAction.CopyAction)

    def keyPressEvent(self, event) -> None:
        """Ask for a plot of the selection when Enter is pressed.

        Inputs:
            event: the QKeyEvent.
        Outputs: none. Other keys are handled by QListWidget.
        """
        # LLFR-00295: Return and Enter, with the focus in the list; the
        # panel checks that a signal is selected (LLFR-00296). Holding
        # the key makes one plot: auto-repeated presses are ignored.
        if event.key() in PLOT_SELECTION_KEY_TUPLE:
            event.accept()
            if not event.isAutoRepeat():
                self.plot_selection_requested.emit()
            return
        super().keyPressEvent(event)

    def selected_name_list(self) -> list:
        """Return the selected signal names, in list order.

        Inputs: none.
        Outputs: a list of str, from top to bottom.
        """
        # LLFR-00295, LLFR-00297: the order of the signal list;
        # LLFR-00643, LLFR-00646: never a file name row.
        return [item.text() for item in self.row_items(SIGNAL_ROW_STR)
                if item.isSelected()]

    def mimeTypes(self) -> list:
        """Return the MIME types used by a drag from this list.

        Inputs: none.
        Outputs: a list with SIGNAL_LIST_MIME_TYPE_STR,
            SIGNAL_MIME_TYPE_STR and PLAIN_TEXT_MIME_TYPE_STR.
        """
        # LLFR-00021, LLFR-00297: the dragged names are offered in these
        # types.
        return [SIGNAL_LIST_MIME_TYPE_STR, SIGNAL_MIME_TYPE_STR,
                PLAIN_TEXT_MIME_TYPE_STR]

    def mimeData(self, item_list: list) -> QMimeData:
        """Build the drag data for the dragged items.

        Inputs:
            item_list: the dragged QListWidgetItem objects, in any
                order.
        Outputs: a QMimeData carrying every signal name, in list order,
            as a JSON list in SIGNAL_LIST_MIME_TYPE_STR, the first name
            as SIGNAL_MIME_TYPE_STR, and the names as text, one per
            line.
        """
        # LLFR-00021, LLFR-00297: the drop target reads the signal names
        # from here, in the order of the signal list; LLFR-00645: never
        # a file name row.
        mime_data = QMimeData()
        sorted_item_list = sorted(
            (item for item in item_list if is_signal_row(item)),
            key=self.row)
        name_list = [item.text() for item in sorted_item_list]
        if not name_list:
            return mime_data
        mime_data.setText("\n".join(name_list))
        # LLFR-00297: the plot widget decodes this JSON as UTF-8.
        mime_data.setData(SIGNAL_LIST_MIME_TYPE_STR, QByteArray(
            json.dumps(name_list).encode(TEXT_ENCODING_STR)))
        # LLFR-00021: the plot widget decodes these bytes as UTF-8.
        mime_data.setData(SIGNAL_MIME_TYPE_STR, QByteArray(
            name_list[0].encode(TEXT_ENCODING_STR)))
        return mime_data


class SignalListPanel(QWidget):
    """Panel placed to the right of the plot panel (HLFR-00001).

    Inputs: none.
    Attributes:
        panel_layout: vertical layout that holds the panel's content.
        title_label: the "Signals" title.
        signal_list_widget: the SignalListWidget with the signal names.
        search_box: the QLineEdit directly below the list, the last row
            of the panel (LLFR-00094, LLFR-00424).
    Signals:
        signal_double_clicked(str): emitted with the name of a signal
            the user double-clicked (LLFR-00019).
        selected_signals_plot_requested(list): emitted with the
            selected names, in list order, when the user presses Enter
            in the list and at least one signal is selected
            (LLFR-00295).
        search_text_changed(str): emitted with the new text each time
            the text of the search box changes (LLFR-00095).
        synthetic_operation_requested(str, str): the signal name and the
            operation id chosen in "Create synthetic signal"
            (LLFR-00239).
        copy_name_requested(str), copy_equation_requested(str),
        rename_signal_requested(str), delete_signal_requested(str): the
            signal name of the chosen menu option (LLFR-00277,
            LLFR-00279, LLFR-00266, LLFR-00255).
        close_file_requested(int): the number of the file whose file
            name row's menu was used to choose "Close file"
            (LLFR-00919).
        close_all_files_requested(): "Close all files" was chosen in
            the file menu (LLFR-00919).
    """

    signal_double_clicked = pyqtSignal(str)
    # LLFR-00295: the selected names, in list order.
    selected_signals_plot_requested = pyqtSignal(list)
    search_text_changed = pyqtSignal(str)
    # LLFR-00239: (signal name, operation id) chosen in the menu.
    synthetic_operation_requested = pyqtSignal(str, str)
    # LLFR-00277, LLFR-00279, LLFR-00266, LLFR-00255: the other options.
    copy_name_requested = pyqtSignal(str)
    copy_equation_requested = pyqtSignal(str)
    rename_signal_requested = pyqtSignal(str)
    delete_signal_requested = pyqtSignal(str)
    # LLFR-00919: the options of the file menu.
    close_file_requested = pyqtSignal(int)
    close_all_files_requested = pyqtSignal()

    def __init__(self) -> None:
        """Create the panel with its title and an empty signal list.

        Inputs: none.
        Outputs: none.
        """
        super().__init__()
        # LLFR-00058: the signal list panel exists and is placed by
        # MainWindow.
        self.setObjectName("signal_list_panel")
        self.panel_layout = QVBoxLayout(self)
        # LLFR-00094: the title, the list and the search box are spaced
        # evenly; the window margins frame the panel.
        self.panel_layout.setContentsMargins(0, 0, 0, 0)
        self.panel_layout.setSpacing(theme.SIGNAL_PANEL_SPACING_I)
        # HLFR-00011: the panel shows the signal names under a title.
        self.title_label = QLabel(TITLE_TEXT_STR)
        self.title_label.setObjectName("signal_list_title")
        self.signal_list_widget = SignalListWidget()
        self.signal_list_widget.setObjectName("signal_list_widget")
        self.panel_layout.addWidget(self.title_label)
        self.panel_layout.addWidget(self.signal_list_widget, 1)
        # LLFR-00094: the search box directly below the list, with
        # nothing between them. LLFR-00424: it is the last row, so its
        # bottom edge is the bottom of the panel's layout, which
        # set_search_box_bottom_margin lines up with the lowest plot.
        self.search_box = QLineEdit()
        self.search_box.setObjectName("signal_search_box")
        self.search_box.setPlaceholderText(SEARCH_PLACEHOLDER_TEXT_STR)
        self.search_box.setClearButtonEnabled(True)
        self.panel_layout.addWidget(self.search_box)
        # LLFR-00019: a double-click passes the signal name on.
        self.signal_list_widget.itemDoubleClicked.connect(
            self._emit_signal_double_clicked)
        # LLFR-00295: Enter in the list plots the selection.
        self.signal_list_widget.plot_selection_requested.connect(
            self.request_selection_plot)
        # LLFR-00095: every change of the text is passed on.
        self.search_box.textChanged.connect(self.search_text_changed.emit)
        # LLFR-00268: the operation groups given by the controller, as
        # (group label, [(operation id, operation label)]).
        self.operation_group_list = []
        # LLFR-00242, LLFR-00251: the synthetic and FFT signal names.
        self.synthetic_name_set = set()
        self.fft_name_set = set()
        # LLFR-00332: the time signal of the opened file, in green.
        self.time_signal_name_set = set()
        # LLFR-00239: the signal and screen point of a pending menu.
        self.pending_menu_tuple = ()
        # LLFR-00919: the file number and screen point of a pending file
        # menu.
        self.pending_file_menu_tuple = ()
        self.signal_list_widget.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu)
        self.signal_list_widget.customContextMenuRequested.connect(
            self.request_signal_menu)

    def show_signal_names(self, signal_name_list: list) -> None:
        """Show names in one group with no file name row.

        Inputs:
            signal_name_list: the signal names, in their order.
        Outputs: none. Used while no file name row is needed, for
            example by tests of the selection.
        """
        # LLFR-00054, LLFR-00935: the names in their order.
        self.show_signal_groups([(None, "", list(signal_name_list), "")])

    def show_signal_groups(self, group_list: list) -> None:
        """Replace the rows of the list with the given groups.

        Inputs:
            group_list: one tuple (file number or None, file name row
                text or "", shown signal names, no-match text or "") per
                group, in list order (LLFR-00934). A group with a row
                text starts with its file name row; a group with a
                no-match text ends with that text.
        Outputs: none.
        """
        # LLFR-00292: the signals still shown stay selected; the others
        # are no longer selected, and stay unselected when shown again.
        kept_selection_set = set(self.selected_signal_names())
        # LLFR-00290: the last clicked signal, where the next Shift +
        # click range starts, is kept too while it is shown.
        current_item = self.signal_list_widget.currentItem()
        current_name_str = ""
        if is_signal_row(current_item):
            current_name_str = current_item.text()
        self.signal_list_widget.clear()
        for number_value, row_str, name_list, no_match_str in group_list:
            # LLFR-00362, LLFR-00650: the file name row of each open
            # file, in the place of LLFR-00934.
            if row_str:
                self.signal_list_widget.addItem(
                    self.build_file_row(str(row_str), number_value))
            # LLFR-00935, LLFR-00639: its shown signals directly below.
            # LLFR-00054: the time signal is shown like any other name.
            for name_str in name_list:
                self.signal_list_widget.addItem(
                    self.build_signal_row(str(name_str)))
            # LLFR-00097, LLFR-00641: "No matching signals" below the
            # row of a file with no match.
            if no_match_str:
                self.signal_list_widget.addItem(
                    self.build_no_match_row(str(no_match_str)))
        signal_item_list = self.signal_list_widget.row_items(
            SIGNAL_ROW_STR)
        for item in signal_item_list:
            if item.text() in kept_selection_set:
                item.setSelected(True)
        for item in signal_item_list:
            if current_name_str and item.text() == current_name_str:
                # LLFR-00290: the current item, without changing the
                # selection, so that Shift + click starts from it.
                self.signal_list_widget.setCurrentItem(
                    item, QItemSelectionModel.SelectionFlag.NoUpdate)
                break
        # LLFR-00649: the tips of the file name rows that are shortened.
        self.signal_list_widget.refresh_file_row_tips()

    def build_signal_row(self, name_str: str) -> QListWidgetItem:
        """Build the row of one signal.

        Inputs:
            name_str: the signal name.
        Outputs: a selectable, draggable QListWidgetItem, in italics for
            a synthetic signal and in green for a time signal.
        """
        # LLFR-00290, LLFR-00297: a signal can be selected and dragged.
        item = QListWidgetItem(name_str)
        item.setData(ROW_KIND_ROLE_I, SIGNAL_ROW_STR)
        # LLFR-00242: synthetic signals are shown in italic letters.
        if name_str in self.synthetic_name_set:
            item_font = item.font()
            item_font.setItalic(True)
            item.setFont(item_font)
        # LLFR-00332: the time signal names in green, also among search
        # results.
        if name_str in self.time_signal_name_set:
            item.setForeground(QBrush(QColor(
                theme.TIME_SIGNAL_TEXT_COLOR_STR)))
        return item

    def build_file_row(self, row_str: str, number_value) -> QListWidgetItem:
        """Build the file name row of one data file.

        Inputs:
            row_str: ``file<N>_<file name>`` (LLFR-00362).
            number_value: the number of the file (LLFR-00896), or None.
        Outputs: a QListWidgetItem in bold that can't be selected or
            dragged (LLFR-00642 to LLFR-00645).
        """
        # LLFR-00362: bold letters.
        item = QListWidgetItem(row_str)
        item.setData(ROW_KIND_ROLE_I, FILE_ROW_STR)
        item.setData(FILE_NUMBER_ROLE_I,
                     None if number_value is None else int(number_value))
        item_font = item.font()
        item_font.setBold(True)
        item.setFont(item_font)
        # LLFR-00643, LLFR-00644, LLFR-00645: shown, but neither
        # selectable nor draggable, so no click, Shift range or drag
        # takes it.
        item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        return item

    def build_no_match_row(self, text_str: str) -> QListWidgetItem:
        """Build the "No matching signals" row of one data file.

        Inputs:
            text_str: the text, "No matching signals".
        Outputs: a QListWidgetItem in a muted color that can't be
            selected or dragged.
        """
        # LLFR-00097, LLFR-00641: the text below the file name row.
        item = QListWidgetItem(text_str)
        item.setData(ROW_KIND_ROLE_I, NO_MATCH_ROW_STR)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        item.setForeground(QBrush(QColor(theme.MUTED_TEXT_COLOR_STR)))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

    def file_row_texts(self) -> list:
        """Return the texts of the file name rows, from top to bottom.

        Inputs: none.
        Outputs: a list of str, ``file<N>_<file name>``; [] while no
            file is open (LLFR-00363).
        """
        # LLFR-00362, LLFR-00934: one row per open file, in number order.
        return [item.text() for item
                in self.signal_list_widget.row_items(FILE_ROW_STR)]

    def row_list(self) -> list:
        """Return every row of the list, from top to bottom.

        Inputs: none.
        Outputs: a list of tuples (kind, text), where kind is
            SIGNAL_ROW_STR, FILE_ROW_STR or NO_MATCH_ROW_STR.
        """
        # LLFR-00934, LLFR-00935, LLFR-00639, LLFR-00641: the order of
        # the rows.
        return [(row_kind(item), item.text())
                for item in self.signal_list_widget.row_items()]

    def set_time_signal_name(self, name_str: str) -> None:
        """Keep which name is the time signal.

        Inputs:
            name_str: the time signal of the opened file, or None.
        Outputs: none. Used by the next show_signal_names.
        """
        # LLFR-00332: the name shown in green.
        self.time_signal_name_set = (set() if name_str is None
                                     else {str(name_str)})

    def set_time_signal_names(self, name_list: list) -> None:
        """Keep which names are the time signals of the open files.

        Inputs:
            name_list: the time signal of each open data file.
        Outputs: none. Used by the next show_signal_names.
        """
        # LLFR-00332: the time signal of each open data file in green.
        self.time_signal_name_set = {str(name_str) for name_str
                                     in name_list}

    def name_color_str(self, name_str: str) -> str:
        """Return the color a shown name is written in.

        Inputs:
            name_str: a shown signal name.
        Outputs: the color as "#rrggbb", the list's text color for a
            name without a color of its own, or "" when the name is not
            shown.
        """
        # LLFR-00332: green for the time signal, other colors otherwise.
        for item in self.signal_list_widget.row_items(SIGNAL_ROW_STR):
            if item.text() != name_str:
                continue
            brush = item.foreground()
            if brush.style() == Qt.BrushStyle.NoBrush:
                return self.signal_list_widget.palette().color(
                    QPalette.ColorRole.Text).name()
            return brush.color().name()
        return ""

    def no_match_message(self) -> str:
        """Return the no-match text when it is shown.

        Inputs: none.
        Outputs: the text of the first "No matching signals" row, or ""
            when no such row is shown.
        """
        # LLFR-00097: what the list says below a file with no match.
        no_match_item_list = self.signal_list_widget.row_items(
            NO_MATCH_ROW_STR)
        if not no_match_item_list:
            return ""
        return no_match_item_list[0].text()

    def set_search_box_bottom_margin(self, bottom_margin_i: int) -> None:
        """Leave room below the search box, so its bottom edge is higher.

        Inputs:
            bottom_margin_i: the space, in pixels, between the bottom edge of
                the search box and the bottom of the panel; a negative
                value is taken as 0.
        Outputs: none.
        """
        # LLFR-00424, LLFR-00652: the main window gives the distance
        # from the bottom of the lowest plot to the bottom of the panel.
        margin_i = max(int(bottom_margin_i), 0)
        if margin_i == self.search_box_bottom_margin():
            return
        self.panel_layout.setContentsMargins(0, 0, 0, margin_i)

    def search_box_bottom_margin(self) -> int:
        """Return the space left below the search box.

        Inputs: none.
        Outputs: the bottom margin of the panel's layout, in pixels.
        """
        # LLFR-00424: the margin of set_search_box_bottom_margin.
        return int(self.panel_layout.contentsMargins().bottom())

    def search_text(self) -> str:
        """Return the text of the search box.

        Inputs: none.
        Outputs: the text, as typed.
        """
        # LLFR-00095: the text the list is filtered with.
        return self.search_box.text()

    def clear_search(self) -> None:
        """Empty the search box.

        Inputs: none.
        Outputs: none. textChanged is emitted when the box had text.
        """
        # LLFR-00104: the search box is cleared on file replace.
        self.search_box.clear()

    def signal_name_list(self) -> list:
        """Return the names shown in the list, from top to bottom.

        Inputs: none.
        Outputs: a list of str.
        """
        # LLFR-00054, LLFR-00935: the names currently shown;
        # LLFR-00642: the file name rows are not signals.
        return [item.text() for item
                in self.signal_list_widget.row_items(SIGNAL_ROW_STR)]

    def selected_signal_names(self) -> list:
        """Return the selected signal names, from top to bottom.

        Inputs: none.
        Outputs: a list of str.
        """
        # LLFR-00290, LLFR-00295: the selection, in list order.
        return self.signal_list_widget.selected_name_list()

    def rename_shown_signal(self, old_name_str: str,
                            new_name_str: str) -> None:
        """Give a shown signal its new name, keeping its selection.

        Inputs:
            old_name_str: the name shown now.
            new_name_str: the new name.
        Outputs: none. The next show_signal_names puts the name in its
            place and keeps it selected (and current) when it was.
        """
        # LLFR-00266, LLFR-00292: a renamed synthetic signal is still
        # shown, so it stays selected.
        for item in self.signal_list_widget.row_items(SIGNAL_ROW_STR):
            if item.text() == old_name_str:
                item.setText(new_name_str)
                return

    def clear_signal_selection(self) -> None:
        """Deselect every signal.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00292: used when a data file is opened or replaced.
        self.signal_list_widget.clearSelection()

    def request_selection_plot(self) -> None:
        """Emit selected_signals_plot_requested when a signal is selected.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00296: with no signal selected, Enter does nothing.
        selected_name_list = self.selected_signal_names()
        if selected_name_list:
            # LLFR-00295: every selected signal, in list order.
            self.selected_signals_plot_requested.emit(selected_name_list)

    def _emit_signal_double_clicked(self, item) -> None:
        """Emit signal_double_clicked with the double-clicked name.

        Inputs:
            item: the QListWidgetItem that was double-clicked.
        Outputs: none.
        """
        # LLFR-00646: a double-click on a file name row plots nothing.
        if not is_signal_row(item):
            return
        # LLFR-00019, LLFR-00294: only the double-clicked signal, whatever
        # other signals are selected.
        self.signal_double_clicked.emit(item.text())

    # ----------------------------------------------------------------
    # Synthetic signals and the signal menu
    # ----------------------------------------------------------------

    def set_operation_groups(self, group_list: list) -> None:
        """Keep the operations listed by "Create synthetic signal".

        Inputs:
            group_list: list of (group label, list of (operation id,
                operation label)), in menu order.
        Outputs: none.
        """
        # LLFR-00268: the groups and operations, in this order.
        self.operation_group_list = [
            (str(group_str), [(str(operation_str), str(label_str))
                              for operation_str, label_str
                              in operation_list])
            for group_str, operation_list in group_list]

    def set_signal_kinds(self, synthetic_name_set: set,
                         fft_name_set: set) -> None:
        """Keep which names are synthetic and which are FFT signals.

        Inputs:
            synthetic_name_set: the synthetic signal names.
            fft_name_set: the FFT signal names among them.
        Outputs: none. Used by the next show_signal_names and menus.
        """
        # LLFR-00242: italics; LLFR-00251, LLFR-00254: the menu options.
        self.synthetic_name_set = set(synthetic_name_set)
        self.fft_name_set = set(fft_name_set)

    def is_name_italic(self, name_str: str) -> bool:
        """Tell whether a shown name is written in italic letters.

        Inputs:
            name_str: a shown signal name.
        Outputs: True when its row uses an italic font.
        """
        # LLFR-00242: synthetic signals in italics.
        for item in self.signal_list_widget.row_items(SIGNAL_ROW_STR):
            if item.text() == name_str:
                return item.font().italic()
        return False

    def signal_menu_and_requests(self, name_str: str) -> tuple:
        """Build the signal menu of a signal and its requests.

        Inputs:
            name_str: the right-clicked signal name.
        Outputs: a tuple (menu, request_list): a QMenu (not shown) whose
            actions hold, as data, the index of their request in
            request_list, a list of functions without arguments that
            emit the request of the option.
        """
        menu = QMenu(self)
        request_list = []

        def add_request_action(target_menu, text_str: str, request):
            """Add an option that runs a request when it is chosen.

            Inputs:
                target_menu: the QMenu to add the option to.
                text_str: the text of the option.
                request: function without arguments.
            Outputs: the new QAction.
            """
            # LLFR-00239: each option emits its own request.
            action = target_menu.addAction(text_str)
            action.setData(len(request_list))
            request_list.append(request)
            return action

        # LLFR-00239, LLFR-00268: the operations, in groups, with only
        # their names (not the names of the new signals).
        create_menu = menu.addMenu(CREATE_SYNTHETIC_TEXT_STR)
        create_menu.setObjectName("create_synthetic_menu")
        for group_str, operation_list in self.operation_group_list:
            create_menu.addSection(group_str)
            for operation_str, label_str in operation_list:
                add_request_action(
                    create_menu, label_str,
                    lambda chosen_str=operation_str:
                    self.synthetic_operation_requested.emit(name_str,
                                                            chosen_str))
        # LLFR-00251: no operation on an FFT signal.
        create_enabled_b = name_str not in self.fft_name_set
        create_menu.setEnabled(create_enabled_b)
        create_menu.menuAction().setEnabled(create_enabled_b)
        menu.addSeparator()
        # LLFR-00277: every signal's name can be copied.
        add_request_action(menu, COPY_NAME_TEXT_STR,
                           lambda: self.copy_name_requested.emit(name_str))
        if name_str in self.synthetic_name_set:
            if name_str not in self.fft_name_set:
                # LLFR-00278: the equation of a synthetic signal that is
                # not an FFT signal (LLFR-00283).
                add_request_action(
                    menu, COPY_EQUATION_TEXT_STR,
                    lambda: self.copy_equation_requested.emit(name_str))
            menu.addSeparator()
            # LLFR-00265, LLFR-00254: only synthetic signals.
            add_request_action(
                menu, RENAME_SIGNAL_TEXT_STR,
                lambda: self.rename_signal_requested.emit(name_str))
            add_request_action(
                menu, DELETE_SIGNAL_TEXT_STR,
                lambda: self.delete_signal_requested.emit(name_str))
        return menu, request_list

    def build_signal_menu(self, name_str: str) -> QMenu:
        """Build the signal menu of a signal, not shown.

        Inputs:
            name_str: the right-clicked signal name.
        Outputs: a QMenu whose actions emit their request when
            triggered, so tests can choose an option without a modal
            menu.
        """
        # LLFR-00239, LLFR-00254, LLFR-00265, LLFR-00277, LLFR-00278.
        menu, request_list = self.signal_menu_and_requests(name_str)
        action_list = list(menu.actions())
        for action in list(action_list):
            if action.menu() is not None:
                action_list.extend(action.menu().actions())
        for action in action_list:
            if action.data() is not None:
                action.triggered.connect(
                    lambda checked_b=False,
                    request=request_list[action.data()]: request())
        return menu

    def request_signal_menu(self, widget_point) -> None:
        """Open the signal menu once the right-click has been handled.

        Inputs:
            widget_point: QPoint of the click, in the list's viewport
                coordinates.
        Outputs: none. A click outside every name opens no menu.
        """
        # LLFR-00239: only a right-click on a signal name opens the menu.
        item = self.signal_list_widget.itemAt(widget_point)
        if item is None:
            return
        global_point = self.signal_list_widget.viewport().mapToGlobal(
            QPoint(widget_point))
        # LLFR-00647: a file name row opens the file menu instead; the
        # selection is kept (LLFR-00643).
        if row_kind(item) == FILE_ROW_STR:
            number_value = item.data(FILE_NUMBER_ROLE_I)
            if number_value is None:
                return
            self.pending_file_menu_tuple = (int(number_value), global_point)
            QTimer.singleShot(0, self.show_pending_file_menu)
            return
        if not is_signal_row(item):
            # LLFR-00097: the "No matching signals" row has no menu.
            return
        # LLFR-00293: only the right-clicked signal is selected before
        # the menu is shown, and the menu acts on it.
        self.signal_list_widget.select_only(item)
        self.pending_menu_tuple = (item.text(), global_point)
        QTimer.singleShot(0, self.show_pending_signal_menu)

    def show_pending_signal_menu(self) -> None:
        """Show the menu asked for by request_signal_menu.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00239: the menu of the right-clicked name.
        if not self.pending_menu_tuple:
            return
        name_str, global_point = self.pending_menu_tuple
        self.pending_menu_tuple = ()
        self.show_signal_menu(name_str, global_point)

    def execute_menu(self, menu, global_point):
        """Run a menu modally and return the chosen action.

        Inputs:
            menu: the QMenu to show.
            global_point: QPoint in screen coordinates.
        Outputs: the chosen QAction, or None when the menu was closed
            without a choice. Tests replace this method to choose an
            option without a real modal menu.
        """
        # LLFR-00239: the modal menu.
        return menu.exec(global_point)

    def show_signal_menu(self, name_str: str, global_point) -> None:
        """Show the signal menu and emit the chosen option's request.

        Inputs:
            name_str: the right-clicked signal name.
            global_point: QPoint in screen coordinates.
        Outputs: none. The request is emitted after the menu has been
            closed and deleted, as the very last step, so the receiver
            may change the list.
        """
        # LLFR-00239, LLFR-00254, LLFR-00265, LLFR-00277, LLFR-00278.
        menu, request_list = self.signal_menu_and_requests(name_str)
        chosen_action = self.execute_menu(menu, global_point)
        request_index = None
        if chosen_action is not None:
            request_index = chosen_action.data()
        menu.deleteLater()
        if isinstance(request_index, int) and (
                0 <= request_index < len(request_list)):
            request_list[request_index]()

    # ----------------------------------------------------------------
    # The file menu
    # ----------------------------------------------------------------

    def file_menu_and_requests(self, number_i: int) -> tuple:
        """Build the file menu of a file name row and its requests.

        Inputs:
            number_i: the number of the file of the right-clicked row.
        Outputs: a tuple (menu, request_list): a QMenu (not shown) with
            "Close file" and "Close all files", in this order, whose
            actions hold, as data, the index of their request in
            request_list, a list of functions without arguments.
        """
        # LLFR-00919: the two options, in this order.
        menu = QMenu(self)
        menu.setObjectName("file_menu")
        request_list = [
            lambda: self.close_file_requested.emit(int(number_i)),
            self.close_all_files_requested.emit]
        for index_i, text_str in enumerate((CLOSE_FILE_TEXT_STR,
                                            CLOSE_ALL_FILES_TEXT_STR)):
            action = menu.addAction(text_str)
            action.setData(index_i)
        return menu, request_list

    def build_file_menu(self, number_i: int) -> QMenu:
        """Build the file menu of a file name row, not shown.

        Inputs:
            number_i: the number of the file of the row.
        Outputs: a QMenu whose actions emit their request when
            triggered, so tests can choose an option without a modal
            menu.
        """
        # LLFR-00919: Close file and Close all files.
        menu, request_list = self.file_menu_and_requests(number_i)
        for action in menu.actions():
            action.triggered.connect(
                lambda checked_b=False,
                request=request_list[action.data()]: request())
        return menu

    def show_pending_file_menu(self) -> None:
        """Show the file menu asked for by request_signal_menu.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00647: the file menu of the right-clicked file name row.
        if not self.pending_file_menu_tuple:
            return
        number_i, global_point = self.pending_file_menu_tuple
        self.pending_file_menu_tuple = ()
        self.show_file_menu(number_i, global_point)

    def show_file_menu(self, number_i: int, global_point) -> None:
        """Show the file menu and emit the chosen option's request.

        Inputs:
            number_i: the number of the file of the row.
            global_point: QPoint in screen coordinates.
        Outputs: none. The request is emitted after the menu has been
            closed and deleted, so the receiver may change the list.
        """
        # LLFR-00919: the user chooses Close file or Close all files.
        menu, request_list = self.file_menu_and_requests(number_i)
        chosen_action = self.execute_menu(menu, global_point)
        request_index = None
        if chosen_action is not None:
            request_index = chosen_action.data()
        menu.deleteLater()
        if isinstance(request_index, int) and (
                0 <= request_index < len(request_list)):
            request_list[request_index]()
