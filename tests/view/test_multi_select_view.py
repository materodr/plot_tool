"""Tests for selecting and plotting several signals (HLFR-00063 to 65).

The first class checks the signal list panel alone: the selection with
the mouse and its modifiers, the selection kept or dropped when the
shown names change, the right-click and double-click, the Enter key and
the drag data. The second class checks the tool key filter over the
signal list (LLFR-00302). The third class runs a real MainWindow and
MainController: Enter in the list, drops of several names on a plot,
the selection cleared on file replace and the tool keys over the list.
No modal dialog or menu is ever left open.
"""

import json
import os
import tempfile
import unittest
from unittest import mock

from tests.support import expand_all_files
from tests.support import covers, get_qt_application, requires_qt
from tests.support import OPEN_FILE_DIALOG_TARGET_STR

from controller.plot_tools import (
    MARKER_TOOL_STR, NO_TOOL_STR, TIP_TOOL_STR, ZOOM_TOOL_STR)

NAME_LIST = ["file1_Time", "file1_speed", "file1_force", "file1_temperature",
             "pressure"]
FILE_TEXT_STR = ("Time,speed,force,temperature\n"
                 "0,1,2,3\n0.5,2,3,4\n1,3,4,5\n")


def send_key(receiver, event_type_name_str: str, key_name_str: str,
             modifier_name_str: str = "NoModifier") -> None:
    """Send one key event to a widget through the application.

    Inputs:
        receiver: the QObject the event is sent to.
        event_type_name_str: name of a QEvent.Type, e.g. "KeyPress".
        key_name_str: name of a Qt.Key, e.g. "Key_Shift".
        modifier_name_str: name of a Qt.KeyboardModifier.
    Outputs: none.
    """
    from PyQt6.QtCore import QEvent, Qt
    from PyQt6.QtGui import QKeyEvent
    from PyQt6.QtWidgets import QApplication
    QApplication.sendEvent(receiver, QKeyEvent(
        getattr(QEvent.Type, event_type_name_str),
        int(getattr(Qt.Key, key_name_str).value),
        getattr(Qt.KeyboardModifier, modifier_name_str), "", False))


@requires_qt
class SelectionPanelTest(unittest.TestCase):
    """The selection of the signal list panel."""

    def setUp(self) -> None:
        """Create and show a signal list panel with names.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from view import signal_list_panel
        self.panel_module = signal_list_panel
        self.panel = signal_list_panel.SignalListPanel()
        self.panel.resize(250, 400)
        self.panel.show()
        self.panel.show_signal_names(NAME_LIST)
        self.widget = self.panel.signal_list_widget
        self.widget.doItemsLayout()
        self.application.processEvents()
        self.plot_request_list = []
        self.panel.selected_signals_plot_requested.connect(
            self.plot_request_list.append)
        self.double_clicked_list = []
        self.panel.signal_double_clicked.connect(
            self.double_clicked_list.append)

    def tearDown(self) -> None:
        """Close and delete the panel.

        Inputs: none.
        Outputs: none.
        """
        self.panel.close()
        self.panel.deleteLater()
        self.application.processEvents()

    def row_point(self, row_i: int):
        """Return the center of a row in the list's viewport.

        Inputs:
            row_i: the row.
        Outputs: a QPoint.
        """
        item_rect = self.widget.visualItemRect(self.widget.item(row_i))
        self.assertFalse(item_rect.isEmpty())
        return item_rect.center()

    def click(self, row_i: int, modifier_name_str: str = "NoModifier"):
        """Left-click a row, with an optional modifier.

        Inputs:
            row_i: the row.
            modifier_name_str: name of a Qt.KeyboardModifier.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        QTest.mouseClick(self.widget.viewport(), Qt.MouseButton.LeftButton,
                         getattr(Qt.KeyboardModifier, modifier_name_str),
                         self.row_point(row_i))
        self.application.processEvents()

    def select(self, name_list: list) -> None:
        """Select exactly the given names.

        Inputs:
            name_list: the names to select.
        Outputs: none.
        """
        self.widget.clearSelection()
        for row_i in range(self.widget.count()):
            item = self.widget.item(row_i)
            item.setSelected(item.text() in name_list)

    def selected(self) -> list:
        """Return the selected names, in list order.

        Inputs: none.
        Outputs: a list of str.
        """
        return self.panel.selected_signal_names()

    @covers("LLFR-00290", "LLFR-00291", "HLFR-00063")
    def test_click_selects_only_that_signal(self) -> None:
        """A plain click selects one signal and deselects the others.

        Inputs: none.
        Outputs: none.
        """
        self.select(["file1_Time", "file1_force"])
        self.click(3)
        self.assertEqual(self.selected(), ["file1_temperature"])
        self.assertTrue(self.widget.item(3).isSelected())
        self.assertEqual([item.text() for item in
                          self.widget.selectedItems()], ["file1_temperature"])

    @covers("LLFR-00290", "LLFR-00291", "HLFR-00063", "LLFR-00625")
    def test_data_tip_key_click_toggles(self) -> None:
        """Ctrl (Cmd on macOS) + click adds or removes one signal.

        Inputs: none.
        Outputs: none.
        """
        self.click(1)
        self.click(3, "ControlModifier")
        self.assertEqual(self.selected(), ["file1_speed", "file1_temperature"])
        self.click(0, "ControlModifier")
        self.assertEqual(self.selected(), ["file1_Time", "file1_speed",
                                           "file1_temperature"])
        self.click(1, "ControlModifier")
        self.assertEqual(self.selected(), ["file1_Time", "file1_temperature"])

    @covers("LLFR-00290", "LLFR-00291", "HLFR-00063", "LLFR-00626")
    def test_shift_click_selects_a_range(self) -> None:
        """Shift + click selects from the last clicked signal.

        Inputs: none.
        Outputs: none.
        """
        self.click(1)
        self.click(3, "ShiftModifier")
        self.assertEqual(self.selected(), ["file1_speed", "file1_force",
                                           "file1_temperature"])
        self.click(4)
        self.click(2, "ShiftModifier")
        self.assertEqual(self.selected(),
                         ["file1_force", "file1_temperature", "pressure"])

    @covers("LLFR-00292", "LLFR-00095", "HLFR-00063", "HLFR-00033",
            "LLFR-00627")
    def test_hidden_signals_are_deselected_for_good(self) -> None:
        """Hidden names lose the selection; shown names keep it.

        Inputs: none.
        Outputs: none.
        """
        self.select(["file1_speed", "file1_force", "pressure"])
        # A search that hides "force".
        self.panel.show_signal_names(["file1_speed", "pressure", "file1_Time"])
        self.assertEqual(self.selected(), ["file1_speed", "pressure"])
        # Shown again, it stays unselected.
        self.panel.show_signal_names(NAME_LIST)
        self.assertEqual(self.selected(), ["file1_speed", "pressure"])
        # A deleted synthetic signal is a name no longer shown.
        self.panel.show_signal_names(["file1_Time", "file1_speed"])
        self.panel.show_signal_names(NAME_LIST)
        self.assertEqual(self.selected(), ["file1_speed"])
        self.panel.clear_signal_selection()
        self.assertEqual(self.selected(), [])

    @covers("LLFR-00293", "LLFR-00239", "HLFR-00063", "LLFR-00628")
    def test_right_click_selects_only_the_clicked_signal(self) -> None:
        """The menu is for the right-clicked signal, then alone selected.

        Inputs: none.
        Outputs: none.
        """
        self.select(["file1_Time", "file1_speed", "file1_force"])
        menu_name_list = []
        self.panel.show_signal_menu = (
            lambda name_str, point: menu_name_list.append(name_str))
        self.panel.request_signal_menu(self.row_point(3))
        self.assertEqual(self.selected(), ["file1_temperature"])
        self.application.processEvents()
        self.assertEqual(menu_name_list, ["file1_temperature"])

    @covers("LLFR-00293", "LLFR-00277", "HLFR-00063", "LLFR-00628")
    def test_right_click_on_a_selected_signal(self) -> None:
        """Right-clicking one of several selected keeps only that one.

        Inputs: none.
        Outputs: none.
        """
        self.select(["file1_speed", "file1_force"])
        copied_list = []
        self.panel.copy_name_requested.connect(copied_list.append)
        self.panel.execute_menu = lambda menu, point: next(
            action for action in menu.actions()
            if action.text() == self.panel_module.COPY_NAME_TEXT_STR)
        self.panel.request_signal_menu(self.row_point(2))
        self.application.processEvents()
        self.assertEqual(self.selected(), ["file1_force"])
        self.assertEqual(copied_list, ["file1_force"])

    @covers("LLFR-00294", "LLFR-00019", "HLFR-00063", "HLFR-00012")
    def test_double_click_reports_only_that_signal(self) -> None:
        """A double-click with others selected reports one name.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        self.select(["file1_Time", "file1_speed", "file1_temperature"])
        self.widget.itemDoubleClicked.emit(self.widget.item(1))
        self.assertEqual(self.double_clicked_list, ["file1_speed"])
        self.select(["file1_Time", "file1_temperature"])
        # A press on the item first, as a real double-click starts with
        # one; the item view only reports a double-click on the item
        # that was pressed. That click leaves only "force" selected.
        self.click(2)
        self.select(["file1_Time", "file1_force", "file1_temperature"])
        QTest.mouseDClick(self.widget.viewport(), Qt.MouseButton.LeftButton,
                          Qt.KeyboardModifier.NoModifier, self.row_point(2))
        self.application.processEvents()
        self.assertEqual(self.double_clicked_list, ["file1_speed",
                                                    "file1_force"])
        self.assertEqual(self.plot_request_list, [])

    @covers("LLFR-00295", "HLFR-00064", "LLFR-00629")
    def test_enter_and_return_request_the_selection(self) -> None:
        """Enter or Return in the list sends the selection in list order.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        self.click(4)
        self.click(1, "ControlModifier")
        self.click(3, "ControlModifier")
        QTest.keyClick(self.widget, Qt.Key.Key_Return)
        QTest.keyClick(self.widget, Qt.Key.Key_Enter,
                       Qt.KeyboardModifier.KeypadModifier)
        self.application.processEvents()
        self.assertEqual(self.plot_request_list,
                         [["file1_speed", "file1_temperature",
                           "pressure"]] * 2)

    @covers("LLFR-00296", "LLFR-00094", "HLFR-00064")
    def test_enter_with_nothing_or_in_the_search_box(self) -> None:
        """No selection, or the focus in the search box: no request.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        self.widget.clearSelection()
        QTest.keyClick(self.widget, Qt.Key.Key_Return)
        self.select(["file1_speed"])
        QTest.keyClick(self.panel.search_box, Qt.Key.Key_Return)
        QTest.keyClick(self.panel.search_box, Qt.Key.Key_Enter)
        self.application.processEvents()
        self.assertEqual(self.plot_request_list, [])

    @covers("LLFR-00290", "HLFR-00063")
    def test_other_keys_still_move_in_the_list(self) -> None:
        """Keys other than Enter keep their list behaviour.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        self.click(1)
        QTest.keyClick(self.widget, Qt.Key.Key_Down)
        self.application.processEvents()
        self.assertEqual(self.selected(), ["file1_force"])
        self.assertEqual(self.plot_request_list, [])

    @covers("LLFR-00295", "HLFR-00064")
    def test_held_enter_requests_one_plot(self) -> None:
        """Auto-repeated Enter presses are ignored.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import QEvent, Qt
        from PyQt6.QtGui import QKeyEvent
        from PyQt6.QtWidgets import QApplication
        self.select(["file1_speed", "file1_force"])
        for auto_repeat_b in (False, True, True, True):
            QApplication.sendEvent(self.widget, QKeyEvent(
                QEvent.Type.KeyPress, int(Qt.Key.Key_Return.value),
                Qt.KeyboardModifier.NoModifier, "", auto_repeat_b))
        self.application.processEvents()
        self.assertEqual(self.plot_request_list, [["file1_speed",
                                                   "file1_force"]])

    @covers("LLFR-00290", "LLFR-00292", "HLFR-00063", "LLFR-00626")
    def test_shift_click_range_starts_at_the_last_click_after_refill(
            self) -> None:
        """A refill of the list keeps the start of the Shift range.

        Inputs: none.
        Outputs: none.
        """
        self.click(2)
        # The list is refilled (a search, a synthetic signal created).
        self.panel.show_signal_names(NAME_LIST + ["file1_int_speed"])
        self.widget.doItemsLayout()
        self.application.processEvents()
        self.assertEqual(self.widget.currentItem().text(), "file1_force")
        self.assertEqual(self.selected(), ["file1_force"])
        self.click(4, "ShiftModifier")
        self.assertEqual(self.selected(),
                         ["file1_force", "file1_temperature", "pressure"])
        # The current item moved with its name to another row.
        self.click(3)
        self.panel.show_signal_names(["file1_Time", "file1_temperature",
                                      "pressure"])
        self.widget.doItemsLayout()
        self.application.processEvents()
        self.click(0, "ShiftModifier")
        self.assertEqual(self.selected(), ["file1_Time", "file1_temperature"])

    @covers("LLFR-00292", "LLFR-00266", "HLFR-00063")
    def test_renamed_signal_stays_selected(self) -> None:
        """A renamed signal keeps its selection after the refill.

        Inputs: none.
        Outputs: none.
        """
        self.panel.show_signal_names(NAME_LIST + ["file1_int_speed"])
        self.select(["file1_force", "file1_int_speed"])
        self.panel.rename_shown_signal("file1_int_speed", "distance")
        self.panel.rename_shown_signal("missing", "other")
        self.panel.show_signal_names(NAME_LIST + ["distance"])
        self.assertEqual(self.selected(), ["file1_force", "distance"])

    @covers("LLFR-00297", "LLFR-00021", "HLFR-00065")
    def test_drag_data_holds_every_name_in_list_order(self) -> None:
        """The drag data lists the names in list order, as JSON.

        Inputs: none.
        Outputs: none.
        """
        item_list = [self.widget.item(3), self.widget.item(0),
                     self.widget.item(1)]
        mime_data = self.widget.mimeData(item_list)
        list_type_str = self.panel_module.SIGNAL_LIST_MIME_TYPE_STR
        self.assertEqual(list_type_str,
                         "application/x-plot-tool-signal-list")
        self.assertTrue(mime_data.hasFormat(list_type_str))
        self.assertEqual(
            json.loads(bytes(mime_data.data(list_type_str)).decode(
                "utf-8")), ["file1_Time", "file1_speed", "file1_temperature"])
        self.assertEqual(bytes(mime_data.data(
            self.panel_module.SIGNAL_MIME_TYPE_STR)).decode("utf-8"),
            "file1_Time")
        self.assertEqual(mime_data.text(),
                         "file1_Time\nfile1_speed\nfile1_temperature")
        model = self.widget.model()
        self.assertIn(list_type_str, model.mimeTypes())
        model_mime_data = model.mimeData([model.index(4, 0),
                                          model.index(2, 0)])
        self.assertEqual(
            json.loads(bytes(model_mime_data.data(list_type_str)).decode(
                "utf-8")), ["file1_force", "pressure"])

    @covers("LLFR-00297", "HLFR-00065")
    def test_press_on_a_selected_signal_keeps_the_selection(self) -> None:
        """A drag from a selected signal carries the whole selection.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        self.click(1)
        self.click(2, "ControlModifier")
        self.click(4, "ControlModifier")
        QTest.mousePress(self.widget.viewport(), Qt.MouseButton.LeftButton,
                         Qt.KeyboardModifier.NoModifier, self.row_point(2))
        self.application.processEvents()
        self.assertTrue(self.widget.pressed_item_was_selected_b)
        self.widget.drag_selection_check()
        self.assertEqual(self.selected(), ["file1_speed", "file1_force",
                                           "pressure"])
        mime_data = self.widget.mimeData(self.widget.selectedItems())
        self.assertEqual(json.loads(bytes(mime_data.data(
            self.panel_module.SIGNAL_LIST_MIME_TYPE_STR)).decode("utf-8")),
            ["file1_speed", "file1_force", "pressure"])
        # A drag is never finished here, so the release goes through.
        self.widget.pressed_item = None
        QTest.mouseRelease(self.widget.viewport(), Qt.MouseButton.LeftButton,
                           Qt.KeyboardModifier.NoModifier,
                           self.row_point(2))
        self.application.processEvents()

    @covers("LLFR-00298", "LLFR-00021", "HLFR-00063", "HLFR-00013",
            "LLFR-00634")
    def test_drag_from_an_unselected_signal_drags_it_alone(self) -> None:
        """A drag from an unselected signal selects only that signal.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        for modifier in (Qt.KeyboardModifier.NoModifier,
                         Qt.KeyboardModifier.ControlModifier):
            with self.subTest(modifier=modifier):
                self.select(["file1_speed", "file1_force"])
                QTest.mousePress(self.widget.viewport(),
                                 Qt.MouseButton.LeftButton, modifier,
                                 self.row_point(3))
                self.application.processEvents()
                self.assertFalse(self.widget.pressed_item_was_selected_b)
                self.widget.drag_selection_check()
                self.assertEqual(self.selected(), ["file1_temperature"])
                QTest.mouseRelease(self.widget.viewport(),
                                   Qt.MouseButton.LeftButton, modifier,
                                   self.row_point(3))
                self.application.processEvents()


@requires_qt
class SelectionAreaKeyFilterTest(unittest.TestCase):
    """The tool keys over the signal list (LLFR-00302)."""

    def setUp(self) -> None:
        """Create a filter with recording callbacks.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from PyQt6.QtWidgets import QLineEdit, QWidget
        from view.tip_key_filter import (
            DELTA_X_KEY_I, MARKER_KEY_I, TIP_KEY_I, ToolKeyFilter)
        self.call_list = []
        self.over_list_b = True
        self.tool_key_filter = ToolKeyFilter(
            {TIP_KEY_I: TIP_TOOL_STR, MARKER_KEY_I: MARKER_TOOL_STR,
             DELTA_X_KEY_I: "delta_x"},
            lambda tool_str: self.call_list.append(tool_str),
            lambda: self.call_list.append("release"), (QLineEdit,))
        self.tool_key_filter.set_selection_area_function(
            lambda: self.over_list_b)
        self.application.installEventFilter(self.tool_key_filter)
        self.widget = QWidget()

    def tearDown(self) -> None:
        """Remove the filter and delete the widget.

        Inputs: none.
        Outputs: none.
        """
        self.application.removeEventFilter(self.tool_key_filter)
        self.tool_key_filter.deleteLater()
        self.widget.deleteLater()
        self.application.processEvents()

    @covers("LLFR-00302", "LLFR-00148", "LLFR-00154", "HLFR-00063",
            "HLFR-00032", "LLFR-00637")
    def test_tip_key_and_shift_do_nothing_over_the_list(self) -> None:
        """Over the list, Ctrl and Shift neither activate nor release.

        Inputs: none.
        Outputs: none.
        """
        for key_str, modifier_str in (("Key_Control", "ControlModifier"),
                                      ("Key_Shift", "ShiftModifier")):
            with self.subTest(key_str=key_str):
                send_key(self.widget, "KeyPress", key_str, modifier_str)
                self.assertFalse(self.tool_key_filter.is_activation_on())
                send_key(self.widget, "KeyRelease", key_str)
        self.assertEqual(self.call_list, [])

    @covers("LLFR-00302", "LLFR-00148", "LLFR-00149", "LLFR-00154")
    def test_keys_work_again_away_from_the_list(self) -> None:
        """Away from the list, Ctrl and Shift hold their tools again.

        Inputs: none.
        Outputs: none.
        """
        self.over_list_b = False
        send_key(self.widget, "KeyPress", "Key_Control", "ControlModifier")
        send_key(self.widget, "KeyRelease", "Key_Control")
        send_key(self.widget, "KeyPress", "Key_Shift", "ShiftModifier")
        send_key(self.widget, "KeyRelease", "Key_Shift")
        self.assertEqual(self.call_list, [TIP_TOOL_STR, "release",
                                          MARKER_TOOL_STR, "release"])

    @covers("LLFR-00302", "LLFR-00197")
    def test_other_tool_keys_are_not_affected(self) -> None:
        """Only the Data tip key and Shift are selection keys.

        Inputs: none.
        Outputs: none.
        """
        send_key(self.widget, "KeyPress", "Key_X")
        send_key(self.widget, "KeyRelease", "Key_X")
        self.assertEqual(self.call_list, ["delta_x", "release"])


@requires_qt
class MultiSelectMainWindowTest(unittest.TestCase):
    """Select and plot several signals in the real main window."""

    def setUp(self) -> None:
        """Create the window and open a file through Open file.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from PyQt6.QtWidgets import QMessageBox
        from controller.main_controller import MainController
        from view.main_window import MainWindow
        self.message_box_class = QMessageBox
        self.temporary_folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_folder.cleanup)
        self.path_str = os.path.join(self.temporary_folder.name, "a.csv")
        with open(self.path_str, "w", encoding="utf-8") as file:
            file.write(FILE_TEXT_STR)
        self.main_window = MainWindow()
        self.main_window.resize(1100, 800)
        self.controller = MainController(self.main_window)
        self.controller.start()
        self.box_record_list = []
        self.box_patch = mock.patch.object(
            QMessageBox, "exec", new=lambda box: self.fake_exec(box))
        self.box_patch.start()
        self.addCleanup(self.box_patch.stop)
        self.panel = self.main_window.signal_list_panel
        self.widget = self.panel.signal_list_widget
        self.top_panel = self.main_window.top_panel
        self.open_file()

    def tearDown(self) -> None:
        """Release any held key and close the window.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.tool_key_filter.handle_keyboard_lost()
        self.main_window.close()
        self.main_window.deleteLater()
        self.application.processEvents()

    def fake_exec(self, box) -> int:
        """Stand-in for QMessageBox.exec that records the box.

        Inputs:
            box: the QMessageBox being shown.
        Outputs: Yes for a question box, otherwise OK (int values).
        """
        self.box_record_list.append(box.text())
        standard_button = self.message_box_class.StandardButton
        if box.icon() == self.message_box_class.Icon.Question:
            return standard_button.Yes.value
        return standard_button.Ok.value

    def open_file(self) -> None:
        """Click Open file with the dialog returning the test file.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        from PyQt6.QtWidgets import QFileDialog
        with mock.patch(OPEN_FILE_DIALOG_TARGET_STR,
                        return_value=self.path_str):
            QTest.mouseClick(self.top_panel.open_file_button,
                             Qt.MouseButton.LeftButton)
            self.application.processEvents()
            # LLFR-01001: the files are collapsed after an open; these
            # tests read the shown signals.
            expand_all_files(self.controller)

    def select(self, name_list: list) -> None:
        """Select exactly the given names in the signal list.

        Inputs:
            name_list: the names to select.
        Outputs: none.
        """
        self.widget.clearSelection()
        for row_i in range(self.widget.count()):
            item = self.widget.item(row_i)
            item.setSelected(item.text() in name_list)

    def press_enter_in_list(self) -> None:
        """Press Return in the signal list.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        QTest.keyClick(self.widget, Qt.Key.Key_Return)
        self.application.processEvents()

    def plot_widgets(self) -> list:
        """Return the plot widgets of the current tab.

        Inputs: none.
        Outputs: a list of PlotWidget.
        """
        plot_panel = self.main_window.plot_panel
        return list(plot_panel.page_dict[plot_panel.current_tab_id()]
                    .plot_widget_list)

    def model_names(self, plot_widget) -> list:
        """Return the curve names of a plot in the model.

        Inputs:
            plot_widget: the PlotWidget.
        Outputs: the names, in curve order.
        """
        plot = self.controller.plot_controller.workspace.find_plot(
            plot_widget.plot_id_i)
        return [curve.signal_name_str for curve in plot.curve_list]

    def drop_selection(self, plot_widget) -> None:
        """Drop the drag data of the selection on a plot.

        Inputs:
            plot_widget: the PlotWidget to drop on.
        Outputs: none.
        """
        from PyQt6.QtCore import QPoint, QPointF, Qt
        from PyQt6.QtGui import QDropEvent
        mime_data = self.widget.mimeData(self.widget.selectedItems())
        center_point = QPoint(plot_widget.width() // 2,
                              plot_widget.height() // 2)
        drop_event = QDropEvent(QPointF(center_point),
                                Qt.DropAction.CopyAction, mime_data,
                                Qt.MouseButton.NoButton,
                                Qt.KeyboardModifier.NoModifier)
        plot_widget.dropEvent(drop_event)
        self.application.processEvents()

    @covers("LLFR-00295", "LLFR-00301", "HLFR-00064", "HLFR-00040",
            "LLFR-00629")
    def test_enter_plots_the_selection_and_one_undo_removes_it(
            self) -> None:
        """Enter makes one plot of the selection; one undo removes it.

        Inputs: none.
        Outputs: none.
        """
        self.select(["file1_temperature", "file1_speed"])
        self.press_enter_in_list()
        plot_widget_list = self.plot_widgets()
        self.assertEqual(len(plot_widget_list), 1)
        self.assertEqual(self.model_names(plot_widget_list[0]),
                         ["file1_speed", "file1_temperature"])
        self.assertEqual(self.box_record_list, [])
        self.main_window.undo_handler()
        self.application.processEvents()
        self.assertEqual(self.plot_widgets(), [])

    @covers("LLFR-00296", "HLFR-00064", "LLFR-00632")
    def test_enter_in_the_search_box_plots_nothing(self) -> None:
        """Enter in the search box creates no plot and no message.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        self.select(["file1_speed"])
        QTest.keyClick(self.panel.search_box, Qt.Key.Key_Return)
        self.widget.clearSelection()
        self.press_enter_in_list()
        self.assertEqual(self.plot_widgets(), [])
        self.assertEqual(self.box_record_list, [])

    @covers("LLFR-00297", "LLFR-00299", "LLFR-00301", "HLFR-00065")
    def test_drop_of_the_selection_on_a_plot(self) -> None:
        """A drop adds the selected signals not yet in the plot.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.signal_double_click_handler("file1_force")
        self.application.processEvents()
        plot_widget = self.plot_widgets()[0]
        self.select(["file1_Time", "file1_force", "file1_temperature"])
        self.drop_selection(plot_widget)
        self.assertEqual(self.model_names(plot_widget),
                         ["file1_force", "file1_Time", "file1_temperature"])
        self.assertEqual(self.box_record_list, [])
        self.main_window.undo_handler()
        self.application.processEvents()
        plot_widget = self.plot_widgets()[0]
        self.assertEqual(self.model_names(plot_widget), ["file1_force"])

    @covers("LLFR-00292", "LLFR-00926", "HLFR-00063", "LLFR-00627")
    def test_closing_the_file_clears_the_selection(self) -> None:
        """After a close no signal of the closed file stays selected.

        Inputs: none.
        Outputs: none.
        """
        self.select(["file1_speed", "file1_force"])
        self.controller.file_controller.close_all_files()
        self.application.processEvents()
        self.assertEqual(self.panel.signal_name_list(), [])
        self.assertEqual(self.panel.selected_signal_names(), [])
        self.open_file()
        self.assertEqual(self.panel.signal_name_list(), [
            "file2_Time", "file2_speed", "file2_force", "file2_temperature"])
        self.assertEqual(self.panel.selected_signal_names(), [])

    @covers("LLFR-00292", "LLFR-00095", "HLFR-00063", "HLFR-00033",
            "LLFR-00627")
    def test_search_keeps_only_shown_signals_selected(self) -> None:
        """A search drops the hidden signals from the selection.

        Inputs: none.
        Outputs: none.
        """
        self.select(["file1_speed", "file1_force"])
        self.panel.search_box.setText("file1_speed")
        self.application.processEvents()
        self.assertEqual(self.panel.selected_signal_names(), ["file1_speed"])
        self.panel.search_box.clear()
        self.application.processEvents()
        self.assertEqual(self.panel.selected_signal_names(), ["file1_speed"])

    def click_name(self, name_str: str,
                   modifier_name_str: str = "NoModifier") -> None:
        """Left-click a shown signal name, with an optional modifier.

        Inputs:
            name_str: the shown name.
            modifier_name_str: name of a Qt.KeyboardModifier.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        self.widget.doItemsLayout()
        self.application.processEvents()
        from view.signal_list_panel import SIGNAL_ROW_STR
        # The rows of the signals only: the file name row is above them.
        row_i = self.panel.signal_name_list().index(name_str)
        item = self.widget.row_items(SIGNAL_ROW_STR)[row_i]
        item_rect = self.widget.visualItemRect(item)
        self.assertFalse(item_rect.isEmpty())
        QTest.mouseClick(self.widget.viewport(), Qt.MouseButton.LeftButton,
                         getattr(Qt.KeyboardModifier, modifier_name_str),
                         item_rect.center())
        self.application.processEvents()

    @covers("LLFR-00290", "LLFR-00292", "LLFR-00095", "HLFR-00063",
            "LLFR-00626")
    def test_shift_click_after_a_search_starts_at_the_last_click(
            self) -> None:
        """Typing a search between the clicks keeps the range start.

        Inputs: none.
        Outputs: none.
        """
        self.click_name("file1_speed")
        self.panel.search_box.setText("e")
        self.application.processEvents()
        self.assertEqual(self.panel.signal_name_list(),
                         ["file1_Time", "file1_speed", "file1_force",
                          "file1_temperature"])
        self.click_name("file1_temperature", "ShiftModifier")
        self.assertEqual(self.panel.selected_signal_names(),
                         ["file1_speed", "file1_force", "file1_temperature"])

    @covers("LLFR-00290", "LLFR-00292", "LLFR-00242", "HLFR-00063",
            "LLFR-00626")
    def test_shift_click_after_a_synthetic_signal_is_created(self) -> None:
        """Creating a synthetic signal between the clicks keeps the start.

        Inputs: none.
        Outputs: none.
        """
        self.click_name("file1_force")
        self.panel.synthetic_operation_requested.emit("file1_speed",
                                                      "integral")
        self.application.processEvents()
        self.assertEqual(self.panel.signal_name_list()[-1], "file1_int_speed")
        self.click_name("file1_int_speed", "ShiftModifier")
        self.assertEqual(self.panel.selected_signal_names(),
                         ["file1_force", "file1_temperature",
                          "file1_int_speed"])

    @covers("LLFR-00292", "LLFR-00266", "HLFR-00063", "HLFR-00060")
    def test_renamed_synthetic_signal_stays_selected(self) -> None:
        """Renaming a selected synthetic signal keeps it selected.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QInputDialog
        self.panel.synthetic_operation_requested.emit("file1_speed",
                                                      "integral")
        self.application.processEvents()
        self.select(["file1_force", "file1_int_speed"])
        with mock.patch.object(QInputDialog, "getText",
                               return_value=("distance", True)):
            self.panel.rename_signal_requested.emit("file1_int_speed")
            self.application.processEvents()
        self.assertEqual(self.panel.signal_name_list()[-1], "file1_distance")
        self.assertEqual(self.panel.selected_signal_names(),
                         ["file1_force", "file1_distance"])

    @covers("LLFR-00302", "LLFR-00148", "LLFR-00154", "HLFR-00032",
            "LLFR-00637")
    def test_tool_keys_over_the_list_keep_the_active_tool(self) -> None:
        """Ctrl and Shift over the list leave the Zoom tool active.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        self.top_panel.plot_tool_button_dict[ZOOM_TOOL_STR].click()
        self.application.processEvents()
        self.panel.setAttribute(Qt.WidgetAttribute.WA_UnderMouse, True)
        self.assertTrue(self.main_window.is_pointer_over_signal_list())
        for key_str, modifier_str in (("Key_Control", "ControlModifier"),
                                      ("Key_Shift", "ShiftModifier")):
            with self.subTest(key_str=key_str):
                send_key(self.widget, "KeyPress", key_str, modifier_str)
                self.application.processEvents()
                self.assertEqual(self.top_panel.active_plot_tool(),
                                 ZOOM_TOOL_STR)
                send_key(self.widget, "KeyRelease", key_str)
                self.application.processEvents()
                self.assertEqual(self.top_panel.active_plot_tool(),
                                 ZOOM_TOOL_STR)
        # Away from the list the Shift key holds the marker tool again.
        self.panel.setAttribute(Qt.WidgetAttribute.WA_UnderMouse, False)
        self.assertFalse(self.main_window.is_pointer_over_signal_list())
        send_key(self.main_window, "KeyPress", "Key_Shift", "ShiftModifier")
        self.application.processEvents()
        self.assertEqual(self.top_panel.active_plot_tool(), MARKER_TOOL_STR)
        send_key(self.main_window, "KeyRelease", "Key_Shift")
        self.application.processEvents()
        self.assertEqual(self.top_panel.active_plot_tool(), NO_TOOL_STR)


if __name__ == "__main__":
    unittest.main()
