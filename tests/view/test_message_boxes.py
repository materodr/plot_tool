"""Tests for the message boxes (HLFR-00002, LLFR-00032, LLFR-00956).

The modal ``exec`` is always patched, so no test waits for a user.
"""

import unittest
from unittest import mock

from tests.support import covers, get_qt_application, requires_qt


@requires_qt
class MessageBoxesTest(unittest.TestCase):
    """Check the content of each box and the answers of the dialogs."""

    def setUp(self) -> None:
        """Get the application and import the module under test.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from PyQt6.QtWidgets import QMessageBox, QWidget
        from view import message_boxes
        self.message_module = message_boxes
        self.message_box_class = QMessageBox
        self.parent_widget = QWidget()

    def tearDown(self) -> None:
        """Delete the parent widget.

        Inputs: none.
        Outputs: none.
        """
        self.parent_widget.deleteLater()
        self.application.processEvents()

    def button_value_set(self, box) -> set:
        """Return the standard buttons of a box as a set of int values.

        Inputs:
            box: a QMessageBox.
        Outputs: a set with the int value of each standard button.
        """
        standard_button_class = self.message_box_class.StandardButton
        return {box.standardButton(button).value
                for button in box.buttons()
                if box.standardButton(button)
                != standard_button_class.NoButton}

    def patch_exec(self, return_value):
        """Patch QMessageBox.exec so it returns at once.

        The boxes that would have been shown are stored in
        ``self.shown_box_list``.

        Inputs:
            return_value: the value exec returns.
        Outputs: the patcher context manager.
        """
        self.shown_box_list = []

        def fake_exec(box):
            """Record the box instead of showing it.

            Inputs:
                box: the QMessageBox whose exec was called.
            Outputs: return_value.
            """
            self.shown_box_list.append(box)
            return return_value

        return mock.patch.object(self.message_box_class, "exec", fake_exec)

    @covers("HLFR-00002")
    def test_file_open_error_box_content(self) -> None:
        """The error box is critical, titled and shows the given message.

        Inputs: none.
        Outputs: none.
        """
        message_str = "The file could not be read: data.csv"
        box = self.message_module.build_file_open_error_box(
            self.parent_widget, message_str)
        self.assertEqual(box.icon(), self.message_box_class.Icon.Critical)
        self.assertEqual(box.windowTitle(), "File Open Error")
        self.assertEqual(self.message_module.FILE_OPEN_ERROR_TITLE_STR,
                         "File Open Error")
        self.assertEqual(box.text(), message_str)
        self.assertEqual(self.button_value_set(box),
                         {self.message_box_class.StandardButton.Ok.value})
        self.assertIs(box.parent(), self.parent_widget)

    @covers("HLFR-00002")
    def test_file_open_error_box_without_parent(self) -> None:
        """The error box can be built without a parent widget.

        Inputs: none.
        Outputs: none.
        """
        box = self.message_module.build_file_open_error_box(
            None, "The file format is not supported.")
        self.assertIsNone(box.parent())
        self.assertEqual(box.text(), "The file format is not supported.")
        box.deleteLater()

    @covers("HLFR-00002")
    def test_show_file_open_error_runs_box(self) -> None:
        """``show_file_open_error`` runs one box with the given message.

        Inputs: none.
        Outputs: none.
        """
        ok_value_i = self.message_box_class.StandardButton.Ok.value
        with self.patch_exec(ok_value_i):
            result = self.message_module.show_file_open_error(
                self.parent_widget, "could not be accessed")
        self.assertIsNone(result)
        self.assertEqual(len(self.shown_box_list), 1)
        shown_box = self.shown_box_list[0]
        self.assertEqual(shown_box.text(), "could not be accessed")
        self.assertEqual(shown_box.icon(),
                         self.message_box_class.Icon.Critical)

    @covers("LLFR-00032", "HLFR-00018", "HLFR-00146")
    def test_full_tab_box_content(self) -> None:
        """The full tab box is information and tells to use a new tab
        or a larger plot matrix, naming the tab's matrix.

        Inputs: none.
        Outputs: none.
        """
        box = self.message_module.build_full_tab_box(self.parent_widget)
        self.assertEqual(box.icon(),
                         self.message_box_class.Icon.Information)
        self.assertNotEqual(box.icon(),
                            self.message_box_class.Icon.Critical)
        self.assertEqual(box.windowTitle(), "Full Tab")
        self.assertEqual(
            box.text(),
            "This tab is full (5 \u00d7 1 matrix). Use a new tab, a "
            "larger matrix from the tab's menu, or delete a plot.")
        self.assertEqual(self.button_value_set(box),
                         {self.message_box_class.StandardButton.Ok.value})
        box = self.message_module.build_full_tab_box(self.parent_widget, 2,
                                                     3)
        self.assertEqual(
            box.text(),
            "This tab is full (2 \u00d7 3 matrix). Use a new tab, a "
            "larger matrix from the tab's menu, or delete a plot.")

    @covers("LLFR-01127", "LLFR-00032", "HLFR-00018")
    def test_full_ten_by_ten_box_says_only_new_tab(self) -> None:
        """With a 10 x 10 matrix the box says only to use a new tab.

        Inputs: none.
        Outputs: none.
        """
        box = self.message_module.build_full_tab_box(self.parent_widget,
                                                     10, 10)
        self.assertEqual(
            box.text(),
            "This tab is full (10 \u00d7 10 matrix). Use a new tab, or "
            "delete a plot.")
        self.assertNotIn("larger", box.text().lower())

    @covers("LLFR-00032")
    def test_show_full_tab_notification_runs_box(self) -> None:
        """``show_full_tab_notification`` runs the information box.

        Inputs: none.
        Outputs: none.
        """
        ok_value_i = self.message_box_class.StandardButton.Ok.value
        with self.patch_exec(ok_value_i):
            self.message_module.show_full_tab_notification(
                self.parent_widget)
        self.assertEqual(len(self.shown_box_list), 1)
        shown_box = self.shown_box_list[0]
        self.assertEqual(shown_box.icon(),
                         self.message_box_class.Icon.Information)
        self.assertEqual(shown_box.text(),
                         self.message_module.full_tab_message_str(5, 1))

    @covers("LLFR-00211", "LLFR-00657")
    def test_tab_name_taken_box_content(self) -> None:
        """The tab name box is information and names the taken name.

        Inputs: none.
        Outputs: none.
        """
        box = self.message_module.build_tab_name_taken_box(
            self.parent_widget, "Engine")
        self.assertEqual(box.icon(),
                         self.message_box_class.Icon.Information)
        self.assertNotEqual(box.icon(),
                            self.message_box_class.Icon.Critical)
        self.assertEqual(box.windowTitle(), "Rename Tab")
        self.assertIn("'Engine'", box.text())
        self.assertIn("already exists", box.text())
        self.assertEqual(self.button_value_set(box),
                         {self.message_box_class.StandardButton.Ok.value})

    @covers("LLFR-00211", "LLFR-00657")
    def test_show_tab_name_taken_notification_runs_box(self) -> None:
        """``show_tab_name_taken_notification`` runs the information box.

        Inputs: none.
        Outputs: none.
        """
        ok_value_i = self.message_box_class.StandardButton.Ok.value
        with self.patch_exec(ok_value_i):
            self.message_module.show_tab_name_taken_notification(
                self.parent_widget, "Tab 1")
        self.assertEqual(len(self.shown_box_list), 1)
        shown_box = self.shown_box_list[0]
        self.assertEqual(shown_box.icon(),
                         self.message_box_class.Icon.Information)
        self.assertEqual(
            shown_box.text(),
            self.message_module.TAB_NAME_TAKEN_MESSAGE_STR.format(
                name="Tab 1"))

    @covers("LLFR-00896")
    def test_open_files_limit_box_content(self) -> None:
        """The limit box is an information box with OK.

        Inputs: none.
        Outputs: none.
        """
        standard_button_class = self.message_box_class.StandardButton
        box = self.message_module.build_open_files_limit_box(
            self.parent_widget, "10 files are already open.")
        self.assertEqual(box.icon(), self.message_box_class.Icon.Information)
        self.assertEqual(box.windowTitle(),
                         self.message_module.OPEN_FILES_LIMIT_TITLE_STR)
        self.assertEqual(box.text(), "10 files are already open.")
        self.assertEqual(self.button_value_set(box),
                         {standard_button_class.Ok.value})

    @covers("LLFR-00956")
    def test_refused_files_box_content(self) -> None:
        """The box of the refused files is an information box with OK.

        Inputs: none.
        Outputs: none.
        """
        standard_button_class = self.message_box_class.StandardButton
        box = self.message_module.build_refused_files_box(
            self.parent_widget, "a.csv: already open as file1.")
        self.assertEqual(box.icon(), self.message_box_class.Icon.Information)
        self.assertEqual(box.windowTitle(),
                         self.message_module.REFUSED_FILES_TITLE_STR)
        self.assertEqual(box.text(), "a.csv: already open as file1.")
        self.assertEqual(self.button_value_set(box),
                         {standard_button_class.Ok.value})

    def close_open_boxes(self) -> None:
        """Reject any open message box, so a failing test never hangs.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QApplication
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, self.message_box_class):
                widget.reject()


@requires_qt
class CloseFilesBoxTest(unittest.TestCase):
    """The questions of the file menu (LLFR-00924, LLFR-00934)."""

    def setUp(self) -> None:
        """Start Qt.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()

    @covers("LLFR-00924", "LLFR-00925", "HLFR-00118")
    def test_close_file_box(self) -> None:
        """The question of the file controller, with Yes and No.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QMessageBox
        from controller.file_controller import close_file_question
        from view import message_boxes
        question_str = close_file_question("file2_run_B.mat", False)
        box = message_boxes.build_close_file_box(None, question_str)
        self.assertEqual(box.windowTitle(), "Close file")
        self.assertEqual(box.text(), question_str)
        self.assertIn("file2_run_B.mat", box.text())
        self.assertEqual(box.icon(), QMessageBox.Icon.Question)
        self.assertEqual(box.standardButtons(),
                         QMessageBox.StandardButton.Yes
                         | QMessageBox.StandardButton.No)
        self.assertIs(box.defaultButton(),
                      box.button(QMessageBox.StandardButton.No))
        box.deleteLater()
        for answer, expected_b in (
                (QMessageBox.StandardButton.Yes.value, True),
                (QMessageBox.StandardButton.No.value, False)):
            with self.subTest(expected_b=expected_b), mock.patch.object(
                    QMessageBox, "exec", return_value=answer):
                self.assertIs(message_boxes.ask_close_file(
                    None, question_str), expected_b)

    @covers("LLFR-00934", "LLFR-00935", "HLFR-00119")
    def test_close_all_files_box(self) -> None:
        """One question for every file, with Yes and No.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QMessageBox
        from controller.file_controller import close_all_files_question
        from view import message_boxes
        question_str = close_all_files_question()
        box = message_boxes.build_close_all_files_box(None, question_str)
        self.assertEqual(box.windowTitle(), "Close all files")
        self.assertEqual(box.text(), question_str)
        self.assertIn("Every flag and every area will be deleted",
                      box.text())
        box.deleteLater()
        with mock.patch.object(QMessageBox, "exec",
                               return_value=QMessageBox.StandardButton.No):
            self.assertFalse(message_boxes.ask_close_all_files(
                None, question_str))
        with mock.patch.object(QMessageBox, "exec",
                               return_value=QMessageBox.StandardButton.Yes):
            self.assertTrue(message_boxes.ask_close_all_files(
                None, question_str))

    @covers("LLFR-00924", "LLFR-00934")
    def test_main_window_asks_with_the_boxes(self) -> None:
        """The main window facade returns the user's answer.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QMessageBox
        from view.main_window import MainWindow
        window = MainWindow()
        self.addCleanup(window.deleteLater)
        record_list = []

        def fake_exec(box) -> int:
            """Record the box and answer Yes.

            Inputs:
                box: the QMessageBox.
            Outputs: Yes.
            """
            record_list.append((box.windowTitle(), box.text()))
            return QMessageBox.StandardButton.Yes.value

        with mock.patch.object(QMessageBox, "exec", new=fake_exec):
            self.assertTrue(window.ask_close_file("Close file1_a.csv?"))
            self.assertTrue(window.ask_close_all_files("Close all?"))
        self.assertEqual(record_list, [("Close file", "Close file1_a.csv?"),
                                       ("Close all files", "Close all?")])


@requires_qt
class ListBoxesTest(unittest.TestCase):
    """The boxes that list items show them numbered (LLFR-00981)."""

    def setUp(self) -> None:
        """Get the application and import the module under test.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from view import message_boxes
        self.message_module = message_boxes

    @covers("LLFR-00980", "LLFR-00981", "LLFR-00982", "LLFR-00983",
            "LLFR-00984", "LLFR-00255")
    def test_delete_question_numbers_the_dependents(self) -> None:
        """The dependents are numbered below their sentence; one
        dependent alone has no number.

        Inputs: none.
        Outputs: none.
        """
        module = self.message_module
        text_str = module.delete_synthetic_signal_text(
            "file1_int_Speed", ["file1_der_int_Speed",
                                "file1_max_der_int_Speed"])
        self.assertEqual(text_str, "\n\n".join([
            module.DELETE_SYNTHETIC_MESSAGE_STR.format(
                name="file1_int_Speed"),
            module.DELETE_DEPENDENTS_MESSAGE_STR,
            "1. file1_der_int_Speed", "2. file1_max_der_int_Speed",
            module.DELETE_CONSEQUENCE_MESSAGE_STR]))
        alone_str = module.delete_synthetic_signal_text(
            "file1_int_Speed", ["file1_der_int_Speed"])
        self.assertIn(module.DELETE_DEPENDENTS_MESSAGE_STR
                      + "\n\nfile1_der_int_Speed\n\n", alone_str)
        box = module.build_delete_synthetic_signal_box(
            None, "file1_int_Speed", ["file1_der_int_Speed",
                                      "file1_max_der_int_Speed"])
        self.assertEqual(box.text(), text_str)
        box.deleteLater()

    @covers("LLFR-00980", "LLFR-00982", "LLFR-00955", "LLFR-00956",
            "LLFR-01176")
    def test_message_boxes_keep_the_numbered_text(self) -> None:
        """The File Open Error box and the refused files box keep the
        numbered list as their plain text and draw it as rich text with
        hanging indents; a text with no list stays plain text.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        text_str = "1. a.csv: could not be read.\n\n2. b.csv: gone."
        for build_function in (self.message_module.build_file_open_error_box,
                               self.message_module.build_refused_files_box):
            with self.subTest(box=build_function.__name__):
                box = build_function(None, text_str)
                self.assertIsInstance(box, self.message_module.ListMessageBox)
                self.assertEqual(box.text(), text_str)
                self.assertEqual(box.textFormat(), Qt.TextFormat.RichText)
                self.assertIn("text-indent:", box.rich_text())
                box.deleteLater()
                plain_box = build_function(None, "a.csv: could not be read.")
                self.assertEqual(plain_box.text(),
                                 "a.csv: could not be read.")
                self.assertEqual(plain_box.textFormat(),
                                 Qt.TextFormat.PlainText)
                plain_box.deleteLater()

    @covers("LLFR-00990", "LLFR-00884", "LLFR-00885", "LLFR-00986")
    def test_scrollable_boxes_wrap_their_lines(self) -> None:
        """The text fields of the load report and of the changed names
        wrap at their width, also inside a long name, and keep the text.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtGui import QTextOption
        from PyQt6.QtWidgets import QTextEdit
        from model.message_lists import list_body_text
        long_name_str = "file1_" + "x" * 400
        text_str = list_body_text([long_name_str] + [
            f"item {index_i}" for index_i in range(10)])
        module = self.message_module
        for dialog, object_name_str in (
                (module.build_layout_report_box(None, text_str),
                 module.LAYOUT_REPORT_TEXT_OBJECT_NAME_STR),
                (module.build_changed_names_box(None, text_str),
                 module.CHANGED_NAMES_TEXT_OBJECT_NAME_STR)):
            with self.subTest(field=object_name_str):
                field = dialog.findChild(module.ListTextField,
                                         object_name_str)
                self.assertEqual(field.plain_text(), text_str)
                self.assertEqual(field.lineWrapMode(),
                                 QTextEdit.LineWrapMode.WidgetWidth)
                self.assertEqual(
                    field.wordWrapMode(),
                    QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
                dialog.resize(600, 400)
                dialog.show()
                self.application.processEvents()
                # LLFR-00990: no horizontal scroll is needed.
                self.assertEqual(field.horizontalScrollBar().maximum(), 0)
                dialog.close()
                dialog.deleteLater()
        self.application.processEvents()


@requires_qt
class BoldMessageTextTest(unittest.TestCase):
    """The main text of every box is bold, in one size (LLFR-01206)."""

    def setUp(self) -> None:
        """Get the application and a parent widget.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from PyQt6.QtWidgets import QWidget
        from view import message_boxes
        self.message_module = message_boxes
        self.parent_widget = QWidget()

    def tearDown(self) -> None:
        """Delete the parent widget.

        Inputs: none.
        Outputs: none.
        """
        self.parent_widget.deleteLater()
        self.application.processEvents()

    def built_box_list(self) -> list:
        """Return one box of each builder of the module.

        Inputs: none.
        Outputs: a list of (name, box) tuples.
        """
        module = self.message_module
        parent = self.parent_widget
        list_text_str = "Intro:\n\n1. first item\n\n2. second item"
        return [
            ("file open", module.build_file_open_error_box(parent, "x")),
            ("full tab", module.build_full_tab_box(parent, 5, 1)),
            ("tab name", module.build_tab_name_taken_box(parent, "Tab 1")),
            ("kind", module.build_plot_kind_mismatch_box(parent)),
            ("limit", module.build_open_files_limit_box(parent, "x")),
            ("refused", module.build_refused_files_box(parent,
                                                       list_text_str)),
            ("unexpected", module.build_unexpected_error_box(parent, "x")),
            ("nothing", module.build_nothing_to_export_box(parent)),
            ("export", module.build_export_error_box(parent, "why")),
            ("replace", module.build_replace_existing_file_box(parent,
                                                               "/a.pdf")),
            ("delete", module.build_delete_synthetic_signal_box(
                parent, "file1_int_x", ["file1_int_int_x"])),
            ("question", module.build_question_box(parent, "Close file",
                                                   list_text_str)),
        ]

    @covers("LLFR-01206", "LLFR-01207", "HLFR-00002")
    def test_every_message_box_text_is_bold_in_one_size(self) -> None:
        """Information boxes, error boxes and questions, with or without
        a list, draw their text label in bold at 13 points.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QLabel
        for name_str, box in self.built_box_list():
            with self.subTest(box=name_str):
                label = box.findChild(
                    QLabel,
                    self.message_module.MESSAGE_BOX_LABEL_OBJECT_NAME_STR)
                self.assertIsNotNone(label)
                box.ensurePolished()
                label.ensurePolished()
                self.assertTrue(label.font().bold())
                self.assertEqual(
                    label.font().pointSize(),
                    self.message_module.MESSAGE_FONT_POINT_SIZE_I)

    @covers("LLFR-01206", "LLFR-01207", "HLFR-00052")
    def test_scrollable_boxes_are_bold_in_one_size(self) -> None:
        """The load report and a long File Open Error box show their
        sentence and their list in bold, at 13 points.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QLabel
        module = self.message_module
        long_text_str = "\n\n".join(f"{index_i}. file {index_i}: bad"
                                    for index_i in range(1, 30))
        report = module.build_layout_report_box(self.parent_widget,
                                                long_text_str)
        error_box = module.build_file_open_error_box(self.parent_widget,
                                                     long_text_str)
        for dialog, field_name_str in (
                (report, module.LAYOUT_REPORT_TEXT_OBJECT_NAME_STR),
                (error_box, module.FILE_OPEN_ERROR_TEXT_OBJECT_NAME_STR)):
            field = dialog.findChild(module.ListTextField, field_name_str)
            self.assertIsNotNone(field)
            field.ensurePolished()
            self.assertTrue(field.font().bold())
            self.assertEqual(field.font().pointSize(),
                             module.MESSAGE_FONT_POINT_SIZE_I)
        intro = report.findChild(QLabel,
                                 module.SCROLLABLE_INTRO_OBJECT_NAME_STR)
        intro.ensurePolished()
        self.assertTrue(intro.font().bold())
        self.assertEqual(intro.font().pointSize(),
                         module.MESSAGE_FONT_POINT_SIZE_I)

    @covers("LLFR-01206")
    def test_style_helper_is_added_once(self) -> None:
        """apply_message_text_style adds the shared style only once.

        Inputs: none.
        Outputs: none.
        """
        box = self.message_module.ListMessageBox(self.parent_widget)
        self.message_module.apply_message_text_style(box)
        self.assertEqual(box.styleSheet().count("font-weight: bold"), 1)
        self.assertIn("qt_msgbox_label", box.styleSheet())


if __name__ == "__main__":
    unittest.main()
