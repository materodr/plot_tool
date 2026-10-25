"""Tests for the unexpected error box and the exception hook (LLFR-00071).

The modal ``exec`` is always patched, so no test waits for a user.
"""

import io
import sys
import unittest
from unittest import mock

from tests.support import covers, get_qt_application, requires_qt


@requires_qt
class ErrorHookTest(unittest.TestCase):
    """Check the box and the hook installed by src/main.py."""

    def setUp(self) -> None:
        """Get the application and a parent widget.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from PyQt6.QtWidgets import QMessageBox, QWidget
        self.message_box_class = QMessageBox
        self.parent_widget = QWidget()
        self.original_hook = sys.excepthook
        self.addCleanup(setattr, sys, "excepthook", self.original_hook)

    def tearDown(self) -> None:
        """Delete the parent widget.

        Inputs: none.
        Outputs: none.
        """
        self.parent_widget.deleteLater()
        self.application.processEvents()

    def raised_error_tuple(self) -> tuple:
        """Raise and catch an error, returning what excepthook gets.

        Inputs: none.
        Outputs: a tuple (type, error, traceback).
        """
        try:
            raise ValueError("bad plot id 42")
        except ValueError:
            return sys.exc_info()

    @covers("LLFR-00071", "HLFR-00002")
    def test_unexpected_error_box_content(self) -> None:
        """The box is critical, titled "Error" and describes the error.

        Inputs: none.
        Outputs: none.
        """
        from view import message_boxes
        box = message_boxes.build_unexpected_error_box(
            self.parent_widget, "ValueError: boom")
        self.assertEqual(box.icon(), self.message_box_class.Icon.Critical)
        self.assertEqual(box.windowTitle(), "Error")
        self.assertIn("ValueError: boom", box.text())
        self.assertIn("unexpected error", box.text())
        with mock.patch.object(self.message_box_class, "exec") as exec_mock:
            message_boxes.show_unexpected_error(self.parent_widget, "x")
        self.assertEqual(exec_mock.call_count, 1)

    @covers("LLFR-00071", "HLFR-00002")
    def test_hook_shows_box_and_prints_traceback(self) -> None:
        """The hook prints the traceback and shows the box; no raise.

        Inputs: none.
        Outputs: none.
        """
        from view.error_hook import make_error_hook
        record_list = []

        def fake_exec(box) -> int:
            """Record a shown box.

            Inputs:
                box: the QMessageBox.
            Outputs: 0.
            """
            record_list.append((box.windowTitle(), box.icon(), box.text()))
            return 0

        error_stream = io.StringIO()
        hook = make_error_hook(self.parent_widget,
                               error_stream=error_stream)
        with mock.patch.object(self.message_box_class, "exec",
                               new=fake_exec):
            hook(*self.raised_error_tuple())
        self.assertEqual(len(record_list), 1)
        title_str, icon, text_str = record_list[0]
        self.assertEqual(title_str, "Error")
        self.assertEqual(icon, self.message_box_class.Icon.Critical)
        self.assertIn("ValueError: bad plot id 42", text_str)
        self.assertIn("Traceback", error_stream.getvalue())
        self.assertIn("bad plot id 42", error_stream.getvalue())

    @covers("LLFR-00071")
    def test_hook_never_raises(self) -> None:
        """A failing box or stream does not make the hook raise.

        Inputs: none.
        Outputs: none.
        """
        from view.error_hook import make_error_hook

        def failing_show(parent, message_str: str) -> None:
            """Fail like a broken box would.

            Inputs:
                parent: unused.
                message_str: unused.
            Outputs: none; always raises.
            """
            raise RuntimeError("no box")

        class FailingStream:
            """A stream whose write always fails."""

            def write(self, text_str: str) -> None:
                """Fail.

                Inputs:
                    text_str: unused.
                Outputs: none; always raises.
                """
                raise OSError("closed")

        hook = make_error_hook(self.parent_widget, failing_show,
                               FailingStream())
        hook(*self.raised_error_tuple())

    @covers("LLFR-00071")
    def test_install_replaces_excepthook(self) -> None:
        """install_error_hook replaces sys.excepthook.

        Inputs: none.
        Outputs: none.
        """
        from view.error_hook import format_error_message, install_error_hook
        install_error_hook(self.parent_widget)
        self.assertIsNot(sys.excepthook, self.original_hook)
        with mock.patch.object(self.message_box_class, "exec") as exec_mock, \
                mock.patch.object(sys, "stderr", io.StringIO()):
            sys.excepthook(*self.raised_error_tuple())
        self.assertEqual(exec_mock.call_count, 1)
        self.assertEqual(format_error_message(KeyError, KeyError()),
                         "KeyError")


if __name__ == "__main__":
    unittest.main()
