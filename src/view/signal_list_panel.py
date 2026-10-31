"""Signal list panel: shows the signals of the opened file.

Below the list there is a search box (HLFR-00033) whose text is passed
to the signal list controller, which decides which names are shown and
gives the text shown when nothing matches (the view does not import the
model, COR-00009).
"""

from PyQt6.QtCore import QByteArray, QMimeData, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView, QLabel, QLineEdit, QListWidget, QVBoxLayout,
    QWidget)

# LLFR-00021: MIME type of a dragged signal name. The plot widget
# accepts drops of this type, so the literal must stay the same there.
SIGNAL_MIME_TYPE_STR = "application/x-plot-tool-signal"
PLAIN_TEXT_MIME_TYPE_STR = "text/plain"
TITLE_TEXT_STR = "Signals"
TEXT_ENCODING_STR = "utf-8"
# LLFR-00094: hint shown in the empty search box.
SEARCH_PLACEHOLDER_TEXT_STR = "Search signals"


class SignalListWidget(QListWidget):
    """List of signal names that can be dragged but not reordered.

    Inputs:
        parent: optional parent widget.
    Attributes:
        no_match_label: label shown inside the list area when no signal
            matches the search (LLFR-00097); hidden by default.
    """

    def __init__(self, parent=None) -> None:
        """Create a single-selection, drag-only list.

        Inputs:
            parent: optional parent widget.
        Outputs: none.
        """
        super().__init__(parent)
        # HLFR-00011: one signal is picked at a time.
        self.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        # LLFR-00021: names can be dragged out, never dropped in or
        # reordered.
        self.setDragEnabled(True)
        self.setAcceptDrops(False)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        # LLFR-00097: text shown inside the list area when no signal
        # matches the search. It is a label, not an item, so it can
        # never be double-clicked or dragged as a signal.
        self.no_match_label = QLabel("", self.viewport())
        self.no_match_label.setObjectName("no_match_label")
        self.no_match_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.no_match_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        no_match_layout = QVBoxLayout(self.viewport())
        no_match_layout.addWidget(self.no_match_label, 0,
                                  Qt.AlignmentFlag.AlignTop)
        self.no_match_label.hide()

    def mimeTypes(self) -> list:
        """Return the MIME types used by a drag from this list.

        Inputs: none.
        Outputs: a list with SIGNAL_MIME_TYPE_STR and
            PLAIN_TEXT_MIME_TYPE_STR.
        """
        # LLFR-00021: a dragged name is offered in both types.
        return [SIGNAL_MIME_TYPE_STR, PLAIN_TEXT_MIME_TYPE_STR]

    def mimeData(self, item_list: list) -> QMimeData:
        """Build the drag data for the dragged items.

        Inputs:
            item_list: the dragged QListWidgetItem objects (one, since
                the list has single selection).
        Outputs: a QMimeData carrying the first item's name as text and
            as SIGNAL_MIME_TYPE_STR.
        """
        # LLFR-00021: the drop target reads the signal name from here.
        mime_data = QMimeData()
        if not item_list:
            return mime_data
        signal_name_str = item_list[0].text()
        mime_data.setText(signal_name_str)
        # LLFR-00021: the plot widget decodes these bytes as UTF-8.
        mime_data.setData(SIGNAL_MIME_TYPE_STR, QByteArray(
            signal_name_str.encode(TEXT_ENCODING_STR)))
        return mime_data


class SignalListPanel(QWidget):
    """Panel placed to the right of the plot panel (HLFR-00001).

    Inputs: none.
    Attributes:
        panel_layout: vertical layout that holds the panel's content.
        title_label: the "Signals" title.
        signal_list_widget: the SignalListWidget with the signal names.
        search_box: the QLineEdit below the list (LLFR-00094).
    Signals:
        signal_double_clicked(str): emitted with the name of a signal
            the user double-clicked (LLFR-00019).
        search_text_changed(str): emitted with the new text each time
            the text of the search box changes (LLFR-00095).
    """

    signal_double_clicked = pyqtSignal(str)
    search_text_changed = pyqtSignal(str)

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
        # HLFR-00011: the panel shows the signal names under a title.
        self.title_label = QLabel(TITLE_TEXT_STR)
        self.signal_list_widget = SignalListWidget()
        self.signal_list_widget.setObjectName("signal_list_widget")
        self.panel_layout.addWidget(self.title_label)
        self.panel_layout.addWidget(self.signal_list_widget, 1)
        # LLFR-00094: the search box is placed directly below the list.
        self.search_box = QLineEdit()
        self.search_box.setObjectName("signal_search_box")
        self.search_box.setPlaceholderText(SEARCH_PLACEHOLDER_TEXT_STR)
        self.search_box.setClearButtonEnabled(True)
        self.panel_layout.addWidget(self.search_box)
        # LLFR-00019: a double-click passes the signal name on.
        self.signal_list_widget.itemDoubleClicked.connect(
            self._emit_signal_double_clicked)
        # LLFR-00095: every change of the text is passed on.
        self.search_box.textChanged.connect(self.search_text_changed.emit)

    def show_signal_names(self, signal_name_list: list) -> None:
        """Replace the shown names with the given ones, in their order.

        Inputs:
            signal_name_list: the signal names of the opened file,
                including the time signal.
        Outputs: none.
        """
        # LLFR-00017: only the names of the new file are shown.
        # LLFR-00054: the time signal is shown like any other name.
        self.signal_list_widget.clear()
        self.signal_list_widget.addItems(
            [str(name_str) for name_str in signal_name_list])

    def show_no_match_message(self, visible_b: bool,
                              message_str: str) -> None:
        """Show or hide the no-match text inside the list area.

        Inputs:
            visible_b: True to show the text, False to hide it.
            message_str: the text to show ("No matching signals").
        Outputs: none.
        """
        # LLFR-00097: the text is shown when no signal matches.
        no_match_label = self.signal_list_widget.no_match_label
        no_match_label.setText(message_str)
        no_match_label.setVisible(visible_b)

    def no_match_message(self) -> str:
        """Return the no-match text when it is shown.

        Inputs: none.
        Outputs: the shown text, or "" when it is hidden.
        """
        # LLFR-00097: what the list area says when nothing matches.
        no_match_label = self.signal_list_widget.no_match_label
        if no_match_label.isHidden():
            return ""
        return no_match_label.text()

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
        # LLFR-00017, LLFR-00054: the names currently shown.
        return [self.signal_list_widget.item(row_i).text()
                for row_i in range(self.signal_list_widget.count())]

    def _emit_signal_double_clicked(self, item) -> None:
        """Emit signal_double_clicked with the double-clicked name.

        Inputs:
            item: the QListWidgetItem that was double-clicked.
        Outputs: none.
        """
        # LLFR-00019: the name of the double-clicked signal.
        self.signal_double_clicked.emit(item.text())
