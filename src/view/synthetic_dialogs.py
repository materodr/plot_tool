"""Dialogs that ask for the parameter of a synthetic signal (HLFR-00053).

- ParameterDialog: asks for numbers (the cutoff frequency and the order
  of a filter, LLFR-00245; the window size of a moving average, LLFR-00269; the
  constant of a Comparison or Arithmetic operation, LLFR-00272). It
  stays open, and says why, while the typed value is not allowed.
- SecondSignalDialog: asks for the second signal of a "Product with
  signal" (LLFR-00275).

The view does not import the model (COR-00009): the controller gives
the prompt, which states the allowed ranges, the fields, and a check
function that returns the reason the typed values are not allowed (""
when they are).

Each dialog is made by a ``build_*`` function, so tests can fill it in
and press its buttons without running it modally.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QButtonGroup, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QRadioButton, QVBoxLayout)

from view import theme

# LLFR-00245: the dialogs are wide enough for the stated range.
MINIMUM_DIALOG_WIDTH_I = 380


class ParameterDialog(QDialog):
    """Dialog with one text field per value of an operation's parameter.

    Inputs:
        parent: parent widget, or None.
        title_str: the window title (the operation's menu label).
        prompt_str: the question, with the allowed ranges.
        field_list: one (label_str, starting text) per value, in order;
            for example the cutoff frequency and the order of a filter.
        check_function: function taking value_list() and returning the
            reason the values are not allowed, or "" when they are.
        choice_tuple: () for no choice, or (label_str, list of
            (choice id, choice label), id chosen at first): one radio
            button per choice, for example how a filter starts.
    Attributes:
        prompt_label: the label with the question.
        field_label_list: the label of each field.
        value_edit_list: the QLineEdit of each field, in order.
        choice_button_dict: choice id -> QRadioButton (empty without a
            choice).
        error_label: the label with the reason, hidden while there is
            none.
        button_box: the OK and Cancel buttons.
    """

    def __init__(self, parent, title_str: str, prompt_str: str,
                 field_list: list, check_function,
                 choice_tuple: tuple = ()) -> None:
        """Create the dialog, not shown.

        Inputs:
            parent: parent widget, or None.
            title_str: the window title.
            prompt_str: the question, with the allowed ranges.
            field_list: (label_str, starting text) per field.
            check_function: value_list() -> reason ("" when allowed).
            choice_tuple: () or (label, [(id, label)], id at first).
        Outputs: none.
        """
        super().__init__(parent)
        # LLFR-00245, LLFR-00269, LLFR-00272: ask for the values.
        self.setWindowTitle(title_str)
        self.setModal(True)
        self.setMinimumWidth(MINIMUM_DIALOG_WIDTH_I)
        self.check_function = check_function
        dialog_layout = QVBoxLayout(self)
        self.prompt_label = QLabel(prompt_str)
        self.prompt_label.setObjectName("parameter_prompt_label")
        self.prompt_label.setWordWrap(True)
        dialog_layout.addWidget(self.prompt_label)
        # LLFR-00245: a filter has two fields, the cutoff and the order,
        # the order starting at 2; the other operations have one.
        field_layout = QFormLayout()
        self.field_label_list = []
        self.value_edit_list = []
        for label_str, starting_text_str in field_list:
            field_label = QLabel(str(label_str))
            value_edit = QLineEdit(str(starting_text_str))
            value_edit.setObjectName("parameter_value_edit")
            field_layout.addRow(field_label, value_edit)
            self.field_label_list.append(field_label)
            self.value_edit_list.append(value_edit)
        # LLFR-00245, LLFR-00246: how a filter starts, one radio button
        # per choice, the default one chosen when the dialog opens.
        self.choice_button_dict = {}
        self.choice_group = QButtonGroup(self)
        if choice_tuple:
            choice_label_str, choice_list, chosen_id_str = choice_tuple
            choice_row_layout = QHBoxLayout()
            for choice_id_str, choice_text_str in choice_list:
                choice_button = QRadioButton(str(choice_text_str))
                self.choice_group.addButton(choice_button)
                choice_row_layout.addWidget(choice_button)
                self.choice_button_dict[str(choice_id_str)] = choice_button
            choice_row_layout.addStretch(1)
            self.choice_label = QLabel(str(choice_label_str))
            field_layout.addRow(self.choice_label, choice_row_layout)
            self.set_choice(str(chosen_id_str))
        dialog_layout.addLayout(field_layout)
        # LLFR-00245, LLFR-00269, LLFR-00272: the reason a value is not
        # allowed, shown in the dialog, which stays open.
        self.error_label = QLabel("")
        self.error_label.setObjectName("parameter_error_label")
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet(
            f"color: {theme.DIALOG_ERROR_TEXT_COLOR_STR};")
        self.error_label.hide()
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.try_accept)
        # LLFR-00245, LLFR-00269, LLFR-00272: Cancel creates nothing.
        self.button_box.rejected.connect(self.reject)
        dialog_layout.addWidget(self.error_label)
        dialog_layout.addWidget(self.button_box)
        if self.value_edit_list:
            self.value_edit_list[0].setFocus()

    def field_label_text_list(self) -> list:
        """Return the labels of the fields.

        Inputs: none.
        Outputs: a list of str, in field order.
        """
        # LLFR-00245: what each field asks for.
        return [field_label.text() for field_label in self.field_label_list]

    def value_text_list(self) -> list:
        """Return the typed texts.

        Inputs: none.
        Outputs: a list of str, one per field, as typed.
        """
        # LLFR-00245, LLFR-00269, LLFR-00272: the controller reads them.
        return [value_edit.text() for value_edit in self.value_edit_list]

    def choice_text_dict(self) -> dict:
        """Return the label of each choice.

        Inputs: none.
        Outputs: a dict choice id -> radio button text.
        """
        # LLFR-00245: "From the first value" and "From zero".
        return {choice_id_str: choice_button.text()
                for choice_id_str, choice_button
                in self.choice_button_dict.items()}

    def chosen_choice(self) -> str:
        """Return the id of the chosen radio button.

        Inputs: none.
        Outputs: the choice id, or "" without a choice.
        """
        # LLFR-00245, LLFR-00246: the filter start the user chose.
        for choice_id_str, choice_button in self.choice_button_dict.items():
            if choice_button.isChecked():
                return choice_id_str
        return ""

    def set_choice(self, choice_id_str: str) -> bool:
        """Choose a radio button.

        Inputs:
            choice_id_str: the id of the choice.
        Outputs: True when the dialog has that choice.
        """
        # LLFR-00245: the user picks how the filter starts.
        choice_button = self.choice_button_dict.get(choice_id_str)
        if choice_button is None:
            return False
        choice_button.setChecked(True)
        return True

    def value_list(self) -> list:
        """Return the typed texts, then the chosen id when there is one.

        Inputs: none.
        Outputs: a list of str.
        """
        # LLFR-00245, LLFR-00246: what the controller checks and reads.
        if not self.choice_button_dict:
            return self.value_text_list()
        return self.value_text_list() + [self.chosen_choice()]

    def set_value_texts(self, text_list: list) -> None:
        """Type texts in the fields.

        Inputs:
            text_list: one text per field, in field order.
        Outputs: none.
        """
        # LLFR-00245, LLFR-00269, LLFR-00272: the values of the user.
        for value_edit, text_str in zip(self.value_edit_list, text_list):
            value_edit.setText(str(text_str))

    def error_text(self) -> str:
        """Return the reason shown in the dialog.

        Inputs: none.
        Outputs: the reason, or "" when none is shown.
        """
        # LLFR-00245, LLFR-00269, LLFR-00272: why the values are refused.
        if self.error_label.isHidden():
            return ""
        return self.error_label.text()

    def try_accept(self) -> None:
        """Close the dialog with OK only when the values are allowed.

        Inputs: none.
        Outputs: none. With a value that is not allowed, the dialog
            stays open and shows the reason.
        """
        # LLFR-00245, LLFR-00269, LLFR-00272: the dialog stays open and
        # says why while a value is outside its range or not a number.
        reason_str = str(self.check_function(self.value_list()) or "")
        if reason_str:
            self.error_label.setText(reason_str)
            self.error_label.show()
            return
        self.error_label.hide()
        self.accept()


class SecondSignalDialog(QDialog):
    """Dialog that lists the signals a product can be computed with.

    Inputs:
        parent: parent widget, or None.
        title_str: the window title ("Product with signal").
        prompt_str: the question.
        name_list: the signal names to choose from, in list order.
        selected_name_str: the name selected when the dialog opens.
    Attributes:
        prompt_label: the label with the question.
        signal_list_widget: the QListWidget with the names.
        button_box: the OK and Cancel buttons.
    """

    def __init__(self, parent, title_str: str, prompt_str: str,
                 name_list: list, selected_name_str: str) -> None:
        """Create the dialog, not shown.

        Inputs:
            parent: parent widget, or None.
            title_str: the window title.
            prompt_str: the question.
            name_list: the names to choose from.
            selected_name_str: the name selected at first.
        Outputs: none.
        """
        super().__init__(parent)
        # LLFR-00275: the user chooses the second signal.
        self.setWindowTitle(title_str)
        self.setModal(True)
        self.setMinimumWidth(MINIMUM_DIALOG_WIDTH_I)
        dialog_layout = QVBoxLayout(self)
        self.prompt_label = QLabel(prompt_str)
        self.prompt_label.setObjectName("second_signal_prompt_label")
        self.prompt_label.setWordWrap(True)
        self.signal_list_widget = QListWidget()
        self.signal_list_widget.setObjectName("second_signal_list")
        self.signal_list_widget.addItems([str(name_str)
                                          for name_str in name_list])
        for row_i, name_str in enumerate(name_list):
            if name_str == selected_name_str:
                self.signal_list_widget.setCurrentRow(row_i)
        if self.signal_list_widget.currentRow() < 0 and name_list:
            self.signal_list_widget.setCurrentRow(0)
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.try_accept)
        # LLFR-00275: Cancel creates nothing.
        self.button_box.rejected.connect(self.reject)
        # LLFR-00275: a double-click chooses the signal at once.
        self.signal_list_widget.itemDoubleClicked.connect(
            lambda *_: self.try_accept())
        dialog_layout.addWidget(self.prompt_label)
        dialog_layout.addWidget(self.signal_list_widget, 1)
        dialog_layout.addWidget(self.button_box)

    def name_list(self) -> list:
        """Return the names listed in the dialog.

        Inputs: none.
        Outputs: a list of str, from top to bottom.
        """
        # LLFR-00275: every signal except the FFT signals.
        return [self.signal_list_widget.item(row_i).text()
                for row_i in range(self.signal_list_widget.count())]

    def chosen_name(self):
        """Return the selected name.

        Inputs: none.
        Outputs: the name, or None when no name is selected.
        """
        # LLFR-00275: the second signal of the product.
        item = self.signal_list_widget.currentItem()
        if item is None:
            return None
        return item.text()

    def select_name(self, name_str: str) -> bool:
        """Select a name in the list.

        Inputs:
            name_str: the name to select.
        Outputs: True when the name is listed.
        """
        # LLFR-00275: the user picks the second signal.
        matching_item_list = self.signal_list_widget.findItems(
            name_str, Qt.MatchFlag.MatchExactly)
        if not matching_item_list:
            return False
        self.signal_list_widget.setCurrentItem(matching_item_list[0])
        return True

    def try_accept(self) -> None:
        """Close the dialog with OK when a name is selected.

        Inputs: none.
        Outputs: none.
        """
        # LLFR-00275: OK needs a chosen signal.
        if self.chosen_name() is None:
            return
        self.accept()


def build_parameter_dialog(parent, title_str: str, prompt_str: str,
                           field_list: list, check_function,
                           choice_tuple: tuple = ()) -> ParameterDialog:
    """Build the dialog that asks for the values of a parameter.

    Inputs:
        parent: parent widget, or None.
        title_str: the window title (the operation's menu label).
        prompt_str: the question, with the allowed ranges.
        field_list: (label_str, starting text) per field.
        check_function: value list -> reason ("" when allowed).
        choice_tuple: () or (label, [(id, label)], id at first).
    Outputs: the ParameterDialog, not shown.
    """
    # LLFR-00245, LLFR-00269, LLFR-00272: one dialog for every number.
    return ParameterDialog(parent, title_str, prompt_str, field_list,
                           check_function, choice_tuple)


def build_second_signal_dialog(parent, title_str: str, prompt_str: str,
                               name_list: list,
                               selected_name_str: str) -> SecondSignalDialog:
    """Build the dialog that asks for the second signal, not shown.

    Inputs:
        parent: parent widget, or None.
        title_str: the window title.
        prompt_str: the question.
        name_list: the names to choose from.
        selected_name_str: the name selected at first.
    Outputs: the SecondSignalDialog.
    """
    # LLFR-00275: the list of the signals a product can use.
    return SecondSignalDialog(parent, title_str, prompt_str, name_list,
                              selected_name_str)


def run_dialog(dialog) -> bool:
    """Run a dialog modally.

    Inputs:
        dialog: a QDialog.
    Outputs: True when the dialog was closed with OK.
    """
    # LLFR-00245, LLFR-00269, LLFR-00272, LLFR-00275: only OK creates.
    result = dialog.exec()
    if isinstance(result, QDialog.DialogCode):
        result = result.value
    return int(result) == QDialog.DialogCode.Accepted.value
