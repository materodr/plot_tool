"""View tests of the synthetic signals (HLFR-00053 to HLFR-00062).

The signal list menu, the parameter dialogs, the delete question, the
information boxes and the clipboard are checked on real widgets; the
end-to-end tests run a real MainWindow and MainController on a CSV
file. Menus and dialogs are never run modally: the tests replace the
methods that run them.
"""

import json
import os
import tempfile
import unittest
from unittest import mock

from tests.support import covers, get_qt_application, requires_qt

DATA_NAME_LIST = ["Time", "Speed", "Torque"]


def operation_group_list() -> list:
    """Return the menu groups as the synthetic controller gives them.

    Inputs: none.
    Outputs: (group label, [(operation id, label)]) tuples.
    """
    from model import synthetic_operations
    return [(group_str, [(operation.operation_str,
                          operation.menu_label_str)
                         for operation in operation_list])
            for group_str, operation_list
            in synthetic_operations.operation_group_list()]


def find_action(menu, text_str: str):
    """Return the action of a menu or of its submenus with a text.

    Inputs:
        menu: a QMenu.
        text_str: the text of the action.
    Outputs: the QAction, or None.
    """
    for action in menu.actions():
        if action.text() == text_str and not action.isSeparator():
            return action
        if action.menu() is not None:
            found_action = find_action(action.menu(), text_str)
            if found_action is not None:
                return found_action
    return None


@requires_qt
class SignalMenuTest(unittest.TestCase):
    """Check the signal menu of the signal list panel."""

    def setUp(self) -> None:
        """Create a panel with data, synthetic and FFT names.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from view.signal_list_panel import SignalListPanel
        self.panel = SignalListPanel()
        self.panel.set_operation_groups(operation_group_list())
        self.panel.set_signal_kinds({"int_Speed", "fft_0s_to_1s_Speed"},
                                    {"fft_0s_to_1s_Speed"})
        self.panel.show_signal_names(DATA_NAME_LIST + [
            "int_Speed", "fft_0s_to_1s_Speed"])
        self.panel.resize(250, 400)
        self.panel.show()
        self.application.processEvents()
        self.request_list = []
        self.panel.synthetic_operation_requested.connect(
            lambda name_str, operation_str: self.request_list.append(
                ("create", name_str, operation_str)))
        self.panel.copy_name_requested.connect(
            lambda name_str: self.request_list.append(
                ("copy_name", name_str)))
        self.panel.copy_equation_requested.connect(
            lambda name_str: self.request_list.append(
                ("copy_equation", name_str)))
        self.panel.rename_signal_requested.connect(
            lambda name_str: self.request_list.append(("rename", name_str)))
        self.panel.delete_signal_requested.connect(
            lambda name_str: self.request_list.append(("delete", name_str)))

    def tearDown(self) -> None:
        """Close and delete the panel.

        Inputs: none.
        Outputs: none.
        """
        self.panel.close()
        self.panel.deleteLater()
        self.application.processEvents()

    def option_text_list(self, name_str: str) -> list:
        """Return the texts of the top level menu options of a signal.

        Inputs:
            name_str: the right-clicked signal.
        Outputs: the texts, separators left out.
        """
        menu = self.panel.build_signal_menu(name_str)
        text_list = [action.text() for action in menu.actions()
                     if not action.isSeparator()]
        menu.deleteLater()
        return text_list

    @covers("LLFR-00239", "LLFR-00277", "LLFR-00254", "LLFR-00265",
            "LLFR-00278", "LLFR-00283")
    def test_options_of_data_and_synthetic_signals(self) -> None:
        """Data signals get Create and Copy name; synthetic ones more.

        Inputs: none.
        Outputs: none.
        """
        for name_str in DATA_NAME_LIST:
            self.assertEqual(self.option_text_list(name_str),
                             ["Create synthetic signal", "Copy name"])
        self.assertEqual(self.option_text_list("int_Speed"), [
            "Create synthetic signal", "Copy name", "Copy equation",
            "Rename", "Delete signal"])
        # LLFR-00278, LLFR-00283: an FFT signal has no equation.
        self.assertEqual(self.option_text_list("fft_0s_to_1s_Speed"), [
            "Create synthetic signal", "Copy name", "Rename",
            "Delete signal"])

    @covers("LLFR-00268", "LLFR-00239")
    def test_create_submenu_lists_the_groups_in_order(self) -> None:
        """The submenu has group headers and only operation labels.

        Inputs: none.
        Outputs: none.
        """
        menu = self.panel.build_signal_menu("Speed")
        create_menu = menu.actions()[0].menu()
        self.assertIsNotNone(create_menu)
        self.assertTrue(menu.actions()[0].isEnabled())
        entry_list = [("section" if action.isSeparator() else "option",
                       action.text()) for action in create_menu.actions()]
        expected_list = []
        for group_str, operation_list in operation_group_list():
            expected_list.append(("section", group_str))
            expected_list.extend(("option", label_str)
                                 for _, label_str in operation_list)
        self.assertEqual(entry_list, expected_list)
        self.assertEqual(expected_list[0], ("section", "Calculus"))
        self.assertEqual(expected_list[-1], ("option", "FFT (fft)"))
        # LLFR-00268: each operation shows its abbreviation.
        self.assertIn(("option", "Low-pass filter (lpf)"), entry_list)
        self.assertIn(("option", "Absolute value (abs)"), entry_list)
        self.assertEqual(entry_list.index(("option", "Absolute value (abs)"))
                         + 1, entry_list.index(
                             ("option", "Product with signal (prod)")))
        # LLFR-00239: no name of a new signal is shown.
        for _, text_str in entry_list:
            self.assertNotIn("_", text_str)
            self.assertNotIn("Speed", text_str)
        menu.deleteLater()

    @covers("LLFR-00251")
    def test_create_is_disabled_for_fft_signals(self) -> None:
        """The Create option of an FFT signal is disabled.

        Inputs: none.
        Outputs: none.
        """
        menu = self.panel.build_signal_menu("fft_0s_to_1s_Speed")
        self.assertEqual(menu.actions()[0].text(),
                         "Create synthetic signal")
        self.assertFalse(menu.actions()[0].isEnabled())
        self.assertFalse(menu.actions()[0].menu().isEnabled())
        menu.deleteLater()
        menu = self.panel.build_signal_menu("int_Speed")
        self.assertTrue(menu.actions()[0].isEnabled())
        menu.deleteLater()

    @covers("LLFR-00239", "LLFR-00277", "LLFR-00278", "LLFR-00265",
            "LLFR-00254")
    def test_options_emit_their_requests(self) -> None:
        """Each option emits its request with the signal name.

        Inputs: none.
        Outputs: none.
        """
        menu = self.panel.build_signal_menu("int_Speed")
        for text_str in ("Moving average (mavg)", "Copy name",
                         "Copy equation",
                         "Rename", "Delete signal"):
            find_action(menu, text_str).trigger()
        menu.deleteLater()
        self.assertEqual(self.request_list, [
            ("create", "int_Speed", "movingaverage"),
            ("copy_name", "int_Speed"),
            ("copy_equation", "int_Speed"),
            ("rename", "int_Speed"),
            ("delete", "int_Speed")])

    @covers("LLFR-00239")
    def test_chosen_option_is_emitted_after_the_menu_closes(self) -> None:
        """show_signal_menu runs the request of the chosen action.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        self.panel.execute_menu = lambda menu, point: find_action(
            menu, "Integral (int)")
        self.panel.show_signal_menu("Torque", QPoint(0, 0))
        self.panel.execute_menu = lambda menu, point: None
        self.panel.show_signal_menu("Torque", QPoint(0, 0))
        self.assertEqual(self.request_list,
                         [("create", "Torque", "integral")])

    @covers("LLFR-00239")
    def test_right_click_opens_the_menu_of_the_clicked_name(self) -> None:
        """A right-click on a name opens its menu once events run.

        Inputs: none.
        Outputs: none.
        """
        shown_list = []
        self.panel.show_signal_menu = (
            lambda name_str, point: shown_list.append(name_str))
        widget = self.panel.signal_list_widget
        item_rectangle = widget.visualItemRect(widget.item(1))
        self.panel.request_signal_menu(item_rectangle.center())
        self.application.processEvents()
        self.assertEqual(shown_list, ["Speed"])
        # LLFR-00239: a click below every name opens no menu.
        from PyQt6.QtCore import QPoint
        self.panel.request_signal_menu(QPoint(5, widget.height() - 3))
        self.application.processEvents()
        self.assertEqual(shown_list, ["Speed"])

    @covers("LLFR-00242")
    def test_synthetic_signals_are_in_italics(self) -> None:
        """Only synthetic names are written in italic letters.

        Inputs: none.
        Outputs: none.
        """
        for name_str in DATA_NAME_LIST:
            self.assertFalse(self.panel.is_name_italic(name_str))
        self.assertTrue(self.panel.is_name_italic("int_Speed"))
        self.assertTrue(self.panel.is_name_italic("fft_0s_to_1s_Speed"))
        self.panel.set_signal_kinds(set(), set())
        self.panel.show_signal_names(DATA_NAME_LIST + ["int_Speed"])
        self.assertFalse(self.panel.is_name_italic("int_Speed"))


@requires_qt
class SyntheticDialogTest(unittest.TestCase):
    """Check the parameter dialogs and the boxes."""

    def setUp(self) -> None:
        """Create the application.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()

    @covers("LLFR-00245")
    def test_filter_dialog_stays_open_and_says_why(self) -> None:
        """OK with a refused value keeps the dialog and shows why.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QDialog
        from view.synthetic_dialogs import build_parameter_dialog
        checked_list = []

        def check(text_list) -> str:
            """Refuse an order of 9.

            Inputs:
                text_list: the typed texts.
            Outputs: the reason or "".
            """
            checked_list.append(list(text_list))
            return "Bad order." if text_list[1] == "9" else ""

        dialog = build_parameter_dialog(
            None, "Low-pass filter", "Cutoff 0 to 5 Hz, order 1 to 8.",
            [("Cutoff frequency (Hz):", ""), ("Filter order:", "2")],
            check, ("Filter start:", [("first_value", "From the first value"),
                                      ("zero", "From zero")],
                    "first_value"))
        # LLFR-00245: two radio buttons, the first value chosen at first.
        self.assertEqual(dialog.choice_text_dict(), {
            "first_value": "From the first value", "zero": "From zero"})
        self.assertEqual(dialog.chosen_choice(), "first_value")
        self.assertFalse(dialog.set_choice("later"))
        self.assertEqual(dialog.windowTitle(), "Low-pass filter")
        self.assertIn("0 to 5 Hz", dialog.prompt_label.text())
        self.assertEqual(dialog.field_label_text_list(),
                         ["Cutoff frequency (Hz):", "Filter order:"])
        self.assertEqual(dialog.value_text_list(), ["", "2"])
        dialog.set_value_texts(["1.5", "9"])
        dialog.try_accept()
        self.assertEqual(dialog.error_text(), "Bad order.")
        self.assertNotEqual(dialog.result(),
                            QDialog.DialogCode.Accepted.value)
        dialog.set_value_texts(["1.5", "4"])
        self.assertTrue(dialog.set_choice("zero"))
        dialog.try_accept()
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted.value)
        self.assertEqual(dialog.error_text(), "")
        self.assertEqual(checked_list, [["1.5", "9", "first_value"],
                                        ["1.5", "4", "zero"]])
        self.assertEqual(dialog.value_list(), ["1.5", "4", "zero"])
        dialog.deleteLater()

    @covers("LLFR-00269", "LLFR-00272")
    def test_cancel_rejects_the_dialog(self) -> None:
        """Cancel closes a one-field dialog without accepting it.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QDialog, QDialogButtonBox
        from view.synthetic_dialogs import build_parameter_dialog
        dialog = build_parameter_dialog(
            None, "Moving average", "From 2 to 10 samples.",
            [("Window size (samples):", "")], lambda text_list: "")
        self.assertEqual(len(dialog.value_edit_list), 1)
        self.assertEqual(dialog.choice_text_dict(), {})
        self.assertEqual(dialog.value_list(), [""])
        dialog.button_box.button(
            QDialogButtonBox.StandardButton.Cancel).click()
        self.assertEqual(dialog.result(), QDialog.DialogCode.Rejected.value)
        dialog.deleteLater()

    @covers("LLFR-00275")
    def test_second_signal_dialog(self) -> None:
        """The dialog lists the names and returns the chosen one.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QDialog
        from view.synthetic_dialogs import build_second_signal_dialog
        dialog = build_second_signal_dialog(
            None, "Product with signal", "Multiply 'Speed' by:",
            ["Time", "Speed", "Torque"], "Speed")
        self.assertEqual(dialog.name_list(), ["Time", "Speed", "Torque"])
        self.assertEqual(dialog.chosen_name(), "Speed")
        self.assertTrue(dialog.select_name("Torque"))
        self.assertFalse(dialog.select_name("Pressure"))
        dialog.try_accept()
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted.value)
        self.assertEqual(dialog.chosen_name(), "Torque")
        dialog.deleteLater()

    def build_search_dialog(self):
        """Build a second signal dialog that searches with the model.

        Inputs: none.
        Outputs: the SecondSignalDialog, not shown, and its names.
        """
        from model.signal_search import NO_MATCH_TEXT_STR, search_signals
        from view.synthetic_dialogs import build_second_signal_dialog
        name_list = ["Time", "Speed", "Torque", "int_Speed",
                     "Engine_Speed"]
        dialog = build_second_signal_dialog(
            None, "Product with signal", "Multiply 'Speed' by:",
            name_list, "Speed",
            lambda text_str: search_signals(name_list, text_str),
            NO_MATCH_TEXT_STR)
        return dialog, name_list

    @covers("LLFR-00285", "LLFR-00157")
    def test_second_signal_search_box_above_the_list_with_focus(
            self) -> None:
        """The search box is above the list and has the focus.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QLineEdit
        from view.main_window import TEXT_INPUT_WIDGET_TUPLE
        dialog, _ = self.build_search_dialog()
        dialog_layout = dialog.layout()
        widget_list = [dialog_layout.itemAt(index_i).widget()
                       for index_i in range(dialog_layout.count())]
        self.assertLess(widget_list.index(dialog.search_box),
                        widget_list.index(dialog.signal_list_widget))
        self.assertIsInstance(dialog.search_box, QLineEdit)
        # LLFR-00157: a text field, so no plot tool key works in it.
        self.assertIsInstance(dialog.search_box, TEXT_INPUT_WIDGET_TUPLE)
        self.assertIs(dialog.focusProxy(), dialog.search_box)
        dialog.show()
        dialog.activateWindow()
        for _ in range(3):
            self.application.processEvents()
        self.assertIs(dialog.focusWidget(), dialog.search_box)
        dialog.reject()
        dialog.deleteLater()

    @covers("LLFR-00285", "LLFR-00095", "LLFR-00096", "LLFR-00097",
            "LLFR-00102", "LLFR-00105", "LLFR-00098", "LLFR-00100",
            "LLFR-00101")
    def test_second_signal_search_filters_the_list(self) -> None:
        """Typing filters the list in the panel's order.

        Inputs: none.
        Outputs: none.
        """
        from model.signal_search import search_signals
        dialog, name_list = self.build_search_dialog()
        self.assertEqual(dialog.name_list(), name_list)
        self.assertEqual(dialog.no_match_text(), "")
        dialog.set_search_text("speed")
        self.assertEqual(dialog.name_list(),
                         ["Speed", "int_Speed", "Engine_Speed"])
        self.assertEqual(dialog.chosen_name(), "Speed")
        for text_str in ("ENGINESPEED", "sped", "int sp", "e", "Tork"):
            dialog.set_search_text(text_str)
            self.assertEqual(dialog.name_list(),
                             search_signals(name_list, text_str))
        dialog.set_search_text("zzz")
        self.assertEqual(dialog.name_list(), [])
        self.assertEqual(dialog.no_match_text(), "No matching signals")
        self.assertIsNone(dialog.chosen_name())
        dialog.set_search_text("   ")
        self.assertEqual(dialog.name_list(), name_list)
        self.assertEqual(dialog.no_match_text(), "")
        dialog.deleteLater()

    @covers("LLFR-00285", "LLFR-00275")
    def test_second_signal_search_accept_and_cancel(self) -> None:
        """Enter takes the selected match; with no match it does nothing.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        from PyQt6.QtWidgets import QDialog, QDialogButtonBox
        dialog, _ = self.build_search_dialog()
        dialog.show()
        self.application.processEvents()
        dialog.set_search_text("zzz")
        QTest.keyClick(dialog.search_box, Qt.Key.Key_Return)
        self.application.processEvents()
        self.assertTrue(dialog.isVisible())
        dialog.button_box.button(QDialogButtonBox.StandardButton.Ok).click()
        self.assertTrue(dialog.isVisible())
        # The selected signal is kept while it is still shown.
        dialog.set_search_text("speed")
        self.assertTrue(dialog.select_name("Engine_Speed"))
        dialog.set_search_text("speed ")
        self.assertEqual(dialog.chosen_name(), "Engine_Speed")
        dialog.set_search_text("torque")
        self.assertEqual(dialog.chosen_name(), "Torque")
        QTest.keyClick(dialog.search_box, Qt.Key.Key_Return)
        self.application.processEvents()
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted.value)
        self.assertEqual(dialog.chosen_name(), "Torque")
        dialog.deleteLater()
        cancel_dialog, _ = self.build_search_dialog()
        cancel_dialog.set_search_text("int")
        cancel_dialog.button_box.button(
            QDialogButtonBox.StandardButton.Cancel).click()
        self.assertEqual(cancel_dialog.result(),
                         QDialog.DialogCode.Rejected.value)
        cancel_dialog.deleteLater()

    @covers("LLFR-00255")
    def test_delete_box_names_the_dependents(self) -> None:
        """The delete question names the dependents; No is the default.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QMessageBox
        from view import message_boxes
        box = message_boxes.build_delete_synthetic_signal_box(
            None, "int_Speed", ["der_int_Speed", "max_der_int_Speed"])
        self.assertEqual(box.icon(), QMessageBox.Icon.Question)
        self.assertIn("'int_Speed'", box.text())
        self.assertIn("der_int_Speed", box.text())
        self.assertIn("max_der_int_Speed", box.text())
        self.assertEqual(box.defaultButton(),
                         box.button(QMessageBox.StandardButton.No))
        box.deleteLater()
        alone_box = message_boxes.build_delete_synthetic_signal_box(
            None, "max_Speed", [])
        self.assertNotIn("computed from it", alone_box.text())
        alone_box.deleteLater()

    @covers("LLFR-00247", "LLFR-00250", "LLFR-00267")
    def test_information_box(self) -> None:
        """The synthetic signal boxes are information boxes.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QMessageBox
        from view import message_boxes
        box = message_boxes.build_signal_information_box(
            None, "Create synthetic signal",
            "The operation needs evenly spaced time samples.")
        self.assertEqual(box.icon(), QMessageBox.Icon.Information)
        self.assertEqual(box.windowTitle(), "Create synthetic signal")
        box.deleteLater()


@requires_qt
class SyntheticEndToEndTest(unittest.TestCase):
    """Open a CSV file and work with synthetic signals in the window."""

    def setUp(self) -> None:
        """Create the window and the controller and open a CSV file.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from PyQt6.QtWidgets import QDialog, QMessageBox
        from controller.main_controller import MainController
        from view.main_window import MainWindow
        self.dialog_class = QDialog
        self.message_box_class = QMessageBox
        self.temporary_folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_folder.cleanup)
        self.path_str = os.path.join(self.temporary_folder.name, "data.csv")
        with open(self.path_str, "w", encoding="utf-8") as data_file:
            data_file.write("Time,Speed,Torque\n")
            for index_i in range(100):
                time_s = index_i * 0.1
                data_file.write(f"{time_s:.1f},{index_i % 7},{index_i}\n")
        self.main_window = MainWindow()
        self.controller = MainController(self.main_window)
        self.controller.start()
        self.application.processEvents()
        self.box_record_list = []
        self.box_answer_list = []
        self.box_patch = mock.patch.object(
            QMessageBox, "exec", new=lambda box: self.fake_exec(box))
        self.box_patch.start()
        self.addCleanup(self.box_patch.stop)
        self.dialog_attempts_list = []
        self.prompt_text_list = []
        self.choice_text_list = []
        self.reason_text_list = []
        self.main_window.run_modal_dialog = self.fake_run_dialog
        self.panel = self.main_window.signal_list_panel
        from PyQt6.QtWidgets import QFileDialog
        with mock.patch.object(QFileDialog, "getOpenFileName",
                               return_value=(self.path_str, "")):
            self.main_window._on_open_file_activated()
        self.application.processEvents()

    def tearDown(self) -> None:
        """Close the main window.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.close()
        self.main_window.deleteLater()
        self.application.processEvents()

    def fake_exec(self, box) -> int:
        """Stand-in for QMessageBox.exec that records the box.

        Inputs:
            box: the QMessageBox being shown.
        Outputs: the next prepared answer for a question (Yes when
            none), otherwise OK.
        """
        self.box_record_list.append(
            (box.windowTitle(), box.icon(), box.text()))
        standard_button = self.message_box_class.StandardButton
        if box.icon() == self.message_box_class.Icon.Question:
            if self.box_answer_list and not self.box_answer_list.pop(0):
                return standard_button.No.value
            return standard_button.Yes.value
        return standard_button.Ok.value

    def fake_run_dialog(self, dialog) -> bool:
        """Fill in a synthetic dialog and press OK, as the user would.

        Each entry of dialog_attempts_list is the list of attempts of
        one dialog: each attempt is a list of texts (one per field, or
        the name to choose); OK is pressed after each attempt, and the
        user cancels when no attempt is accepted.

        Inputs:
            dialog: the dialog the window would run.
        Outputs: True when the dialog accepted an attempt.
        """
        if not self.dialog_attempts_list:
            return False
        accepted_i = self.dialog_class.DialogCode.Accepted.value
        for text_list in self.dialog_attempts_list.pop(0):
            if hasattr(dialog, "set_value_texts"):
                dialog.set_value_texts(text_list)
                if len(text_list) > len(dialog.value_edit_list):
                    dialog.set_choice(text_list[-1])
                self.choice_text_list.append(dialog.choice_text_dict())
                self.prompt_text_list.append(dialog.prompt_label.text())
            else:
                dialog.select_name(text_list[0])
            dialog.try_accept()
            if dialog.result() == accepted_i:
                return True
            self.reason_text_list.append(dialog.error_text())
        return False

    def choose(self, name_str: str, option_str: str) -> None:
        """Right-click a signal name and choose an option of its menu.

        Inputs:
            name_str: the signal name.
            option_str: the text of the option.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint
        self.panel.execute_menu = lambda menu, point: find_action(
            menu, option_str)
        self.panel.show_signal_menu(name_str, QPoint(0, 0))
        self.application.processEvents()

    def plot_widget_list(self) -> list:
        """Return the plot widgets of the current tab, top to bottom.

        Inputs: none.
        Outputs: a list of PlotWidget.
        """
        plot_panel = self.main_window.plot_panel
        return [plot_panel.plot_view(plot_id_i) for plot_id_i
                in plot_panel.plot_id_list(plot_panel.current_tab_id())]

    def legend_names(self, plot_widget) -> list:
        """Return the names in a plot's legend.

        Inputs:
            plot_widget: a PlotWidget.
        Outputs: the legend names, in curve order.
        """
        return [name_str for name_str, _ in plot_widget.legend_entry_list()]

    @covers("LLFR-00239", "LLFR-00242", "LLFR-00245", "LLFR-00019",
            "LLFR-00021", "LLFR-00255", "LLFR-00051")
    def test_create_plot_and_delete_with_dependents(self) -> None:
        """Integral and low-pass are created, plotted and deleted.

        Inputs: none.
        Outputs: none.
        """
        self.choose("Speed", "Integral (int)")
        self.dialog_attempts_list = [[["9", "2"], ["2", "3", "zero"]]]
        self.choose("int_Speed", "Low-pass filter (lpf)")
        self.assertIn("less than 5 Hz", self.prompt_text_list[0])
        self.assertIn("from 1 to 8", self.prompt_text_list[0])
        self.assertEqual(len(self.reason_text_list), 1)
        self.assertIn("less than 5 Hz", self.reason_text_list[0])
        self.assertEqual(self.choice_text_list[0], {
            "first_value": "From the first value", "zero": "From zero"})
        self.assertEqual(self.controller.synthetic_controller.store.get(
            "lpf_2Hz_order3_int_Speed").parameter, (2.0, 3, "zero"))
        self.assertEqual(self.panel.signal_name_list(), [
            "Time", "Speed", "Torque", "int_Speed",
            "lpf_2Hz_order3_int_Speed"])
        self.assertTrue(self.panel.is_name_italic("lpf_2Hz_order3_int_Speed"))
        self.assertFalse(self.panel.is_name_italic("Speed"))
        # LLFR-00019, LLFR-00021: plotted like data signals.
        self.panel.signal_double_clicked.emit("lpf_2Hz_order3_int_Speed")
        self.panel.signal_double_clicked.emit("Torque")
        self.application.processEvents()
        first_widget, second_widget = self.plot_widget_list()
        self.controller.plot_controller.on_signal_dropped(
            second_widget.plot_id_i, "int_Speed")
        self.application.processEvents()
        self.assertEqual(self.legend_names(first_widget),
                         ["lpf_2Hz_order3_int_Speed"])
        self.assertEqual(self.legend_names(second_widget),
                         ["Torque", "int_Speed"])
        # LLFR-00255: the question names the dependent; Yes deletes.
        self.choose("int_Speed", "Delete signal")
        title_str, _, text_str = self.box_record_list[-1]
        self.assertEqual(title_str, "Delete signal")
        self.assertIn("lpf_2Hz_order3_int_Speed", text_str)
        self.assertEqual(self.panel.signal_name_list(),
                         ["Time", "Speed", "Torque"])
        remaining_list = self.plot_widget_list()
        self.assertEqual(len(remaining_list), 1)
        self.assertEqual(self.legend_names(remaining_list[0]), ["Torque"])
        self.assertFalse(self.main_window.is_undo_enabled())

    @covers("LLFR-00266", "LLFR-00267", "LLFR-00277", "LLFR-00279")
    def test_rename_and_clipboard(self) -> None:
        """Rename updates the legend; names and equations are copied.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QApplication, QInputDialog
        self.choose("Speed", "Integral (int)")
        self.panel.signal_double_clicked.emit("int_Speed")
        self.application.processEvents()
        with mock.patch.object(QInputDialog, "getText",
                               return_value=(" Distance ", True)):
            self.choose("int_Speed", "Rename")
        self.assertEqual(self.panel.signal_name_list()[-1], "Distance")
        self.assertTrue(self.panel.is_name_italic("Distance"))
        self.assertEqual(self.legend_names(self.plot_widget_list()[0]),
                         ["Distance"])
        with mock.patch.object(QInputDialog, "getText",
                               return_value=("Torque", True)):
            self.choose("Distance", "Rename")
        self.assertIn("already exists", self.box_record_list[-1][2])
        self.assertEqual(self.box_record_list[-1][1],
                         self.message_box_class.Icon.Information)
        self.choose("Torque", "Copy name")
        self.assertEqual(QApplication.clipboard().text(), "Torque")
        self.choose("Distance", "Copy equation")
        self.assertEqual(json.loads(QApplication.clipboard().text()), [
            {"name": "Distance", "operation": "integral",
             "signals": ["Speed"], "parameter": None}])

    @covers("LLFR-00275", "LLFR-00272", "LLFR-00252")
    def test_product_constant_and_file_replace(self) -> None:
        """Product and constant dialogs work; a new file clears them.

        Inputs: none.
        Outputs: none.
        """
        self.dialog_attempts_list = [[["Torque"]], [["x"], ["0"]]]
        self.choose("Speed", "Product with signal (prod)")
        self.assertEqual(self.panel.signal_name_list()[-1],
                         "Speed_prod_Torque")
        # "x" and 0 are refused and the dialog is cancelled after them.
        self.choose("Speed", "Divide by constant (div)")
        self.assertEqual(len(self.panel.signal_name_list()), 4)
        self.assertEqual(self.reason_text_list, [
            "The constant must be a number.",
            "The constant must not be 0 for a division."])
        self.dialog_attempts_list = [[["4"]]]
        self.choose("Speed", "Divide by constant (div)")
        self.assertEqual(self.panel.signal_name_list()[-1], "div_4_Speed")
        from PyQt6.QtWidgets import QFileDialog
        with mock.patch.object(QFileDialog, "getOpenFileName",
                               return_value=(self.path_str, "")):
            self.main_window._on_open_file_activated()
        self.application.processEvents()
        self.assertEqual(self.panel.signal_name_list(),
                         ["Time", "Speed", "Torque"])
        self.assertEqual(self.controller.synthetic_controller.store.names(),
                         [])


if __name__ == "__main__":
    unittest.main()
