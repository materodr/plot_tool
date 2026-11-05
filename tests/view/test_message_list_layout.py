"""Tests of how the boxes that list items draw their lines.

- Each wrapped line of a numbered item continues under the text of its
  own item, not at the left edge of the box (LLFR-01176), in the message
  boxes and in the scrollable boxes.
- The File Open Error box and the refused files box are scrollable when
  they are long (LLFR-01177).

The modal ``exec`` is always patched, so no test waits for a user.
"""

import unittest
from unittest import mock

from tests.support import covers, get_qt_application, requires_qt

# A width at which the long items below wrap onto several lines.
NARROW_TEXT_WIDTH_I = 160
# The largest difference, in pixels, between two positions that must be
# the same.
POSITION_TOLERANCE_F = 1.0
LONG_ITEM_STR = ("this reason is long enough to be wrapped onto several "
                 "lines in a narrow box")


def laid_out_block_list(document, text_width_i: int) -> list:
    """Lay out a text document at a width and return its blocks.

    Inputs:
        document: the QTextDocument.
        text_width_i: the width to lay the text out at, in pixels.
    Outputs: the QTextBlock objects of the document, in order, laid out.
    """
    document.setTextWidth(text_width_i)
    # Asking for the size lays out the whole document.
    document.documentLayout().documentSize()
    block_list = []
    block = document.begin()
    while block.isValid():
        block_list.append(block)
        block = block.next()
    return block_list


@requires_qt
class HangingIndentTest(unittest.TestCase):
    """A wrapped line goes under the text of its own item (LLFR-01176)."""

    def setUp(self) -> None:
        """Get the application and import the modules under test.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from PyQt6.QtGui import QFontMetricsF, QTextDocument
        from PyQt6.QtWidgets import QApplication
        from model import message_lists
        from view import message_boxes
        self.lists_module = message_lists
        self.message_module = message_boxes
        self.font = QApplication.font()
        self.font_metrics = QFontMetricsF(self.font)
        self.document_class = QTextDocument

    def document_of(self, html_str: str):
        """Return a text document that holds rich text in self.font.

        Inputs:
            html_str: the rich text.
        Outputs: the QTextDocument.
        """
        document = self.document_class()
        document.setDefaultFont(self.font)
        document.setHtml(html_str)
        return document

    def assert_close(self, first_f: float, second_f: float) -> None:
        """Check that two positions are the same, within a pixel.

        Inputs:
            first_f, second_f: the two positions, in pixels.
        Outputs: none.
        """
        self.assertLessEqual(abs(first_f - second_f), POSITION_TOLERANCE_F,
                             f"{first_f} != {second_f}")

    def assert_hanging_layout(self, document, text_str: str,
                              text_width_i: int) -> None:
        """Check every line of a list text laid out in a document.

        Each line of text_str is one block. Its first line starts at the
        width of its indent, and its text, and every wrapped line, start
        at the width of its indent and its number.

        Inputs:
            document: the QTextDocument that shows text_str.
            text_str: the plain text of the list box.
            text_width_i: the width to lay the document out at.
        Outputs: none.
        """
        line_tuple_list = self.lists_module.list_line_list(text_str)
        block_list = laid_out_block_list(document, text_width_i)
        self.assertEqual(len(block_list), len(line_tuple_list))
        # The heading or the first line of an item with no indent is
        # where the left edge of the text is.
        left_edge_f = None
        wrapped_count_i = 0
        for block, (indent_str, number_str, rest_str) in zip(
                block_list, line_tuple_list):
            self.assertEqual(block.text(), number_str + rest_str)
            if not (number_str or rest_str):
                continue
            layout = block.layout()
            if left_edge_f is None:
                self.assertEqual(indent_str, "")
                left_edge_f = layout.lineAt(0).x() + (
                    self.font_metrics.horizontalAdvance(indent_str))
            hanging_f = self.font_metrics.horizontalAdvance(
                indent_str + number_str)
            # The number starts after the indent.
            self.assert_close(
                layout.lineAt(0).x() - left_edge_f,
                self.font_metrics.horizontalAdvance(indent_str))
            # The text after the number, and every wrapped line, start at
            # the width of the indent and the number.
            self.assert_close(
                layout.lineAt(0).x()
                + self.font_metrics.horizontalAdvance(number_str)
                - left_edge_f, hanging_f)
            for line_index_i in range(1, layout.lineCount()):
                wrapped_count_i += 1
                self.assert_close(
                    layout.lineAt(line_index_i).x() - left_edge_f,
                    hanging_f)
        # The test text really wraps.
        self.assertGreater(wrapped_count_i, 0)

    @covers("LLFR-01176", "LLFR-00980", "LLFR-00985", "LLFR-00986")
    def test_wrapped_lines_under_the_text_of_their_item(self) -> None:
        """In the rich text of a list, a wrapped line starts under the
        text of its item, for one-digit and two-digit numbers and for a
        sub-line of an item.

        Inputs: none.
        Outputs: none.
        """
        item_list = [f"{LONG_ITEM_STR} {index_i}" for index_i in range(11)]
        item_list[1] = "short\n" + LONG_ITEM_STR
        text_str = self.lists_module.list_text(item_list, "Heading:")
        html_str = self.message_module.list_text_html(text_str, self.font)
        document = self.document_of(html_str)
        self.assert_hanging_layout(document, text_str, NARROW_TEXT_WIDTH_I)
        # The block formats hold the hanging indent of each line.
        block_list = laid_out_block_list(document, NARROW_TEXT_WIDTH_I)
        number_block = block_list[2]
        self.assertEqual(number_block.text(), "1. " + item_list[0])
        self.assert_close(number_block.blockFormat().leftMargin(),
                          self.font_metrics.horizontalAdvance(
                              self.lists_module.FIGURE_SPACE_STR + "1. "))
        self.assert_close(number_block.blockFormat().textIndent(),
                          -self.font_metrics.horizontalAdvance("1. "))

    @covers("LLFR-01176", "LLFR-01178", "LLFR-00985")
    def test_list_inside_an_item_hangs_twice(self) -> None:
        """A numbered list inside an item, such as the sample-count
        error in the File Open Error box, hangs under its own text.

        Inputs: none.
        Outputs: none.
        """
        lists_module = self.lists_module
        inner_str = lists_module.list_text(
            [f"'Signal_{index_i}' {LONG_ITEM_STR}." for index_i in range(3)],
            "The file 'a.mat' cannot be opened because its signals have "
            "different sample counts:")
        text_str = lists_module.list_body_text(
            [inner_str, "b.csv: " + LONG_ITEM_STR])
        html_str = self.message_module.list_text_html(text_str, self.font)
        self.assert_hanging_layout(self.document_of(html_str), text_str,
                                   NARROW_TEXT_WIDTH_I)

    @covers("LLFR-01176", "LLFR-00982")
    def test_rich_text_keeps_the_words_and_blank_lines(self) -> None:
        """The rich text holds the same lines, numbers and blank lines,
        and escapes the characters of HTML.

        Inputs: none.
        Outputs: none.
        """
        text_str = self.lists_module.list_body_text(
            ["<b>a</b> & b", "x  y"])
        document = self.document_of(
            self.message_module.list_text_html(text_str, self.font))
        self.assertEqual(document.toPlainText(),
                         "1. <b>a</b> & b\n\n2. x  y")

    @covers("LLFR-01176", "LLFR-00981", "LLFR-00255", "LLFR-00924",
            "LLFR-00934", "LLFR-00559")
    def test_every_message_box_with_a_list_hangs(self) -> None:
        """The message boxes of LLFR-00981 draw their list as rich text
        with hanging indents and keep their plain text in text().

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QLabel, QMessageBox
        module = self.message_module
        list_str = self.lists_module.list_text(
            ["first " + LONG_ITEM_STR, "second " + LONG_ITEM_STR],
            "These are the items:")
        box_list = [
            module.build_file_open_error_box(None, list_str),
            module.build_refused_files_box(None, list_str),
            module.build_delete_synthetic_signal_box(
                None, "file1_int_Speed", ["file1_a", "file1_b"]),
            module.build_close_file_box(None, list_str),
            module.build_close_all_files_box(None, list_str),
            module.build_signals_save_error_box(None, list_str)]
        for box in box_list:
            with self.subTest(box=box.windowTitle()):
                self.assertIsInstance(box, module.ListMessageBox)
                self.assertIsInstance(box, QMessageBox)
                self.assertEqual(box.textFormat(), Qt.TextFormat.RichText)
                label = box.findChild(QLabel,
                                      module.MESSAGE_BOX_LABEL_OBJECT_NAME_STR)
                self.assertIsNotNone(label)
                self.assertEqual(label.text(), box.rich_text())
                plain_str = box.text()
                self.assertNotIn("<p", plain_str)
                document = self.document_class()
                document.setDefaultFont(label.font())
                document.setHtml(box.rich_text())
                self.assertEqual(document.blockCount(),
                                 len(plain_str.split("\n")))
                box.deleteLater()
        self.assertEqual(box_list[0].text(), list_str)

    @covers("LLFR-01176", "LLFR-00990", "LLFR-00884", "LLFR-00885")
    def test_scrollable_fields_hang_their_wrapped_lines(self) -> None:
        """The text fields of the load report and of the changed names
        draw a wrapped line under the text of its item.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtGui import QFontMetricsF
        module = self.message_module
        text_str = self.lists_module.list_text(
            [f"{LONG_ITEM_STR} {index_i}" for index_i in range(12)],
            "Renamed:")
        for dialog, object_name_str in (
                (module.build_layout_report_box(None, text_str),
                 module.LAYOUT_REPORT_TEXT_OBJECT_NAME_STR),
                (module.build_changed_names_box(None, text_str),
                 module.CHANGED_NAMES_TEXT_OBJECT_NAME_STR)):
            with self.subTest(field=object_name_str):
                field = dialog.findChild(module.ListTextField,
                                         object_name_str)
                self.assertTrue(field.isReadOnly())
                self.assertEqual(field.plain_text(), text_str)
                self.font = field.font()
                self.font_metrics = QFontMetricsF(self.font)
                self.assert_hanging_layout(field.document(), text_str,
                                           NARROW_TEXT_WIDTH_I)
                dialog.deleteLater()


@requires_qt
class LongBoxTest(unittest.TestCase):
    """Long File Open Error and refused files boxes scroll (LLFR-01177)."""

    def setUp(self) -> None:
        """Get the application and import the modules under test.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from model.message_lists import list_body_text
        from view import message_boxes
        self.message_module = message_boxes
        self.long_text_str = list_body_text(
            [f"run_{index_i}.csv: the file could not be read."
             for index_i in range(40)])
        # 8 items and their 7 blank lines: 15 lines, not long.
        self.short_text_str = list_body_text(
            [f"run_{index_i}.csv: gone." for index_i in range(8)])

    @covers("LLFR-01177", "LLFR-00955", "LLFR-00956", "LLFR-00884")
    def test_long_boxes_are_scrollable(self) -> None:
        """A long File Open Error box or refused files box is a dialog
        with a scrollable, read-only field that holds the whole list, its
        title and its icon.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QDialog, QMessageBox
        module = self.message_module
        for build_function, title_str, object_name_str in (
                (module.build_file_open_error_box,
                 module.FILE_OPEN_ERROR_TITLE_STR,
                 module.FILE_OPEN_ERROR_TEXT_OBJECT_NAME_STR),
                (module.build_refused_files_box,
                 module.REFUSED_FILES_TITLE_STR,
                 module.REFUSED_FILES_TEXT_OBJECT_NAME_STR)):
            with self.subTest(box=title_str):
                dialog = build_function(None, self.long_text_str)
                self.assertIsInstance(dialog, QDialog)
                self.assertNotIsInstance(dialog, QMessageBox)
                self.assertEqual(dialog.windowTitle(), title_str)
                field = dialog.findChild(module.ListTextField,
                                         object_name_str)
                self.assertIsNotNone(field)
                self.assertTrue(field.isReadOnly())
                self.assertEqual(field.plain_text(), self.long_text_str)
                dialog.resize(600, 300)
                dialog.show()
                self.application.processEvents()
                # LLFR-00884: the list is longer than the field: it
                # scrolls.
                self.assertGreater(field.verticalScrollBar().maximum(), 0)
                dialog.close()
                dialog.deleteLater()
                # LLFR-01177: a short box stays a message box.
                box = build_function(None, self.short_text_str)
                self.assertIsInstance(box, module.ListMessageBox)
                self.assertEqual(box.windowTitle(), title_str)
                box.deleteLater()
        self.application.processEvents()

    @covers("LLFR-01177", "LLFR-00955", "HLFR-00002")
    def test_long_file_open_error_keeps_its_icon(self) -> None:
        """The scrollable File Open Error box shows the critical icon,
        and the refused files box the information icon.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QLabel, QStyle
        module = self.message_module
        for build_function, pixmap in (
                (module.build_file_open_error_box,
                 QStyle.StandardPixmap.SP_MessageBoxCritical),
                (module.build_refused_files_box,
                 QStyle.StandardPixmap.SP_MessageBoxInformation)):
            with self.subTest(pixmap=pixmap):
                dialog = build_function(None, self.long_text_str)
                expected_image = dialog.style().standardIcon(pixmap).pixmap(
                    module.LAYOUT_REPORT_ICON_SIZE_I,
                    module.LAYOUT_REPORT_ICON_SIZE_I).toImage()
                image_list = [label.pixmap().toImage()
                              for label in dialog.findChildren(QLabel)
                              if not label.pixmap().isNull()]
                self.assertEqual(len(image_list), 1)
                self.assertEqual(image_list[0], expected_image)
                dialog.deleteLater()

    @covers("LLFR-01177", "LLFR-00955", "LLFR-00956")
    def test_main_window_shows_the_long_boxes(self) -> None:
        """The main window runs the scrollable boxes for long texts.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QDialog
        from view.main_window import MainWindow
        module = self.message_module
        window = MainWindow()
        self.addCleanup(window.deleteLater)
        record_list = []

        def fake_exec(dialog) -> int:
            """Record the dialog and its text, and close it.

            Inputs:
                dialog: the QDialog being shown.
            Outputs: the value of Accepted.
            """
            field = dialog.findChild(module.ListTextField)
            record_list.append((dialog.windowTitle(), field.plain_text()))
            return QDialog.DialogCode.Accepted.value

        with mock.patch.object(QDialog, "exec", new=fake_exec):
            window.show_file_open_error(self.long_text_str)
            window.show_refused_files_notification(self.long_text_str)
        self.assertEqual(record_list, [
            (module.FILE_OPEN_ERROR_TITLE_STR, self.long_text_str),
            (module.REFUSED_FILES_TITLE_STR, self.long_text_str)])


if __name__ == "__main__":
    unittest.main()
