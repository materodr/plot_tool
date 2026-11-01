"""Signal list panel: shows the signals of the opened file.

Below the list there is a search box (HLFR-00033) whose text is passed
to the signal list controller, which decides which names are shown and
gives the text shown when nothing matches (the view does not import the
model, COR-00009).

A right-click on a signal name opens the signal menu (LLFR-00239):
"Create synthetic signal" with the operations given by the controller,
in groups (LLFR-00268), disabled for an FFT signal (LLFR-00251); "Copy
name" (LLFR-00277); and, for a synthetic signal, "Copy equation"
(LLFR-00278), "Rename" (LLFR-00265) and "Delete signal" (LLFR-00254).
Synthetic signals are shown in italics (LLFR-00242). The menu is shown
once the right-click has been handled, and its request is emitted after
the menu is closed, so a request may change the list safely.
"""

from PyQt6.QtCore import QByteArray, QMimeData, QPoint, Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView, QLabel, QLineEdit, QListWidget, QMenu, QVBoxLayout,
    QWidget)

from view import theme

# LLFR-00021: MIME type of a dragged signal name. The plot widget
# accepts drops of this type, so the literal must stay the same there.
SIGNAL_MIME_TYPE_STR = "application/x-plot-tool-signal"
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
        # LLFR-00021, LLFR-00154: a drag only copies the name, also with
        # Shift or Cmd held, so that Qt never removes the dragged row.
        self.setDefaultDropAction(Qt.DropAction.CopyAction)
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

    def supportedDropActions(self):
        """Return the drop actions a drag from this list may end with.

        Inputs: none.
        Outputs: Qt.DropAction.CopyAction only.
        """
        # LLFR-00021, LLFR-00154: never a move, which would remove the
        # row from the list.
        return Qt.DropAction.CopyAction

    def startDrag(self, supported_actions) -> None:
        """Start dragging the selected signal name, as a copy only.

        Inputs:
            supported_actions: the Qt.DropAction flags Qt proposes; they
                are replaced by CopyAction.
        Outputs: none.
        """
        # LLFR-00021, LLFR-00154: with Shift (or Cmd on macOS) held, Qt
        # would make the drop a move and then delete the dragged row;
        # offering only a copy keeps the signal list unchanged.
        super().startDrag(Qt.DropAction.CopyAction)

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
        synthetic_operation_requested(str, str): the signal name and the
            operation id chosen in "Create synthetic signal"
            (LLFR-00239).
        copy_name_requested(str), copy_equation_requested(str),
        rename_signal_requested(str), delete_signal_requested(str): the
            signal name of the chosen menu option (LLFR-00277,
            LLFR-00279, LLFR-00266, LLFR-00255).
    """

    signal_double_clicked = pyqtSignal(str)
    search_text_changed = pyqtSignal(str)
    # LLFR-00239: (signal name, operation id) chosen in the menu.
    synthetic_operation_requested = pyqtSignal(str, str)
    # LLFR-00277, LLFR-00279, LLFR-00266, LLFR-00255: the other options.
    copy_name_requested = pyqtSignal(str)
    copy_equation_requested = pyqtSignal(str)
    rename_signal_requested = pyqtSignal(str)
    delete_signal_requested = pyqtSignal(str)

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
        # LLFR-00268: the operation groups given by the controller, as
        # (group label, [(operation id, operation label)]).
        self.operation_group_list = []
        # LLFR-00242, LLFR-00251: the synthetic and FFT signal names.
        self.synthetic_name_set = set()
        self.fft_name_set = set()
        # LLFR-00239: the signal and screen point of a pending menu.
        self.pending_menu_tuple = ()
        self.signal_list_widget.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu)
        self.signal_list_widget.customContextMenuRequested.connect(
            self.request_signal_menu)

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
        # LLFR-00242: synthetic signals are shown in italic letters.
        for row_i in range(self.signal_list_widget.count()):
            item = self.signal_list_widget.item(row_i)
            if item.text() in self.synthetic_name_set:
                item_font = item.font()
                item_font.setItalic(True)
                item.setFont(item_font)

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
        for row_i in range(self.signal_list_widget.count()):
            item = self.signal_list_widget.item(row_i)
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
