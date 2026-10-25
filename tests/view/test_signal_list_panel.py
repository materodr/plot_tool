"""Tests for the signal list panel (HLFR-00011)."""

import unittest

from tests.support import covers, get_qt_application, requires_qt

NAME_LIST = ["Time", "speed", "force", "temperature"]


@requires_qt
class SignalListPanelTest(unittest.TestCase):
    """Check the names, double-click and drag data of the signal list."""

    def setUp(self) -> None:
        """Create and show a signal list panel.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from view import signal_list_panel
        self.panel_module = signal_list_panel
        self.panel = signal_list_panel.SignalListPanel()
        self.panel.resize(250, 400)
        self.panel.show()
        self.application.processEvents()
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

    @covers("LLFR-00054")
    def test_panel_starts_empty_with_title(self) -> None:
        """A new panel shows the "Signals" title and no names.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.panel.title_label.text(), "Signals")
        self.assertEqual(self.panel.signal_name_list(), [])

    @covers("LLFR-00054", "LLFR-00017")
    def test_names_shown_in_file_order_with_time(self) -> None:
        """The names are shown in the given order, Time included.

        Inputs: none.
        Outputs: none.
        """
        self.panel.show_signal_names(NAME_LIST)
        self.assertEqual(self.panel.signal_name_list(), NAME_LIST)
        widget = self.panel.signal_list_widget
        self.assertEqual(widget.count(), len(NAME_LIST))
        self.assertEqual(widget.item(0).text(), "Time")

    @covers("LLFR-00017")
    def test_new_names_replace_old_ones(self) -> None:
        """Showing a new file's names removes the previous names.

        Inputs: none.
        Outputs: none.
        """
        self.panel.show_signal_names(NAME_LIST)
        self.panel.show_signal_names(["Time", "pressure"])
        self.assertEqual(self.panel.signal_name_list(),
                         ["Time", "pressure"])
        self.panel.show_signal_names([])
        self.assertEqual(self.panel.signal_name_list(), [])

    @covers("LLFR-00019")
    def test_double_click_emits_signal_name(self) -> None:
        """Double-clicking an item emits its name once.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        self.panel.show_signal_names(NAME_LIST)
        self.application.processEvents()
        widget = self.panel.signal_list_widget
        # Lay the items out now, so their rectangles are known.
        widget.doItemsLayout()
        self.application.processEvents()
        item_rect = widget.visualItemRect(widget.item(2))
        self.assertFalse(item_rect.isEmpty())
        center = item_rect.center()
        # A press on the item first, as a real double-click starts
        # with one; the item view only reports a double-click on the
        # item that was pressed.
        QTest.mouseClick(widget.viewport(), Qt.MouseButton.LeftButton,
                         Qt.KeyboardModifier.NoModifier, center)
        QTest.mouseDClick(widget.viewport(), Qt.MouseButton.LeftButton,
                          Qt.KeyboardModifier.NoModifier, center)
        self.application.processEvents()
        self.assertEqual(self.double_clicked_list, ["force"])

    @covers("LLFR-00019", "LLFR-00055")
    def test_item_double_clicked_signal_emits_time(self) -> None:
        """The Time item is passed on like any other name.

        Inputs: none.
        Outputs: none.
        """
        self.panel.show_signal_names(NAME_LIST)
        widget = self.panel.signal_list_widget
        widget.itemDoubleClicked.emit(widget.item(0))
        self.assertEqual(self.double_clicked_list, ["Time"])

    @covers("LLFR-00021", "LLFR-00055")
    def test_mime_data_carries_both_types(self) -> None:
        """The drag data has the name as plain text and custom type.

        Inputs: none.
        Outputs: none.
        """
        self.panel.show_signal_names(NAME_LIST)
        widget = self.panel.signal_list_widget
        for row_i, name_str in enumerate(NAME_LIST):
            with self.subTest(name_str=name_str):
                mime_data = widget.mimeData([widget.item(row_i)])
                self.assertTrue(mime_data.hasText())
                self.assertEqual(mime_data.text(), name_str)
                self.assertTrue(mime_data.hasFormat(
                    self.panel_module.SIGNAL_MIME_TYPE_STR))
                self.assertEqual(
                    bytes(mime_data.data(
                        self.panel_module.SIGNAL_MIME_TYPE_STR)).decode(
                            "utf-8"),
                    name_str)

    @covers("LLFR-00021")
    def test_non_ascii_name_round_trips_as_utf8(self) -> None:
        """A non-ASCII name decodes back from the custom MIME bytes.

        Inputs: none.
        Outputs: none.
        """
        name_str = "Temperatur \u00b0C \u00fc"
        self.panel.show_signal_names(["Time", name_str])
        widget = self.panel.signal_list_widget
        mime_data = widget.mimeData([widget.item(1)])
        payload_bytes = bytes(mime_data.data(
            self.panel_module.SIGNAL_MIME_TYPE_STR))
        self.assertEqual(payload_bytes, name_str.encode("utf-8"))
        self.assertEqual(payload_bytes.decode("utf-8"), name_str)
        self.assertEqual(mime_data.text(), name_str)

    @covers("LLFR-00021")
    def test_model_drag_data_uses_override(self) -> None:
        """The data Qt builds for a drag goes through the override.

        Inputs: none.
        Outputs: none.
        """
        self.panel.show_signal_names(NAME_LIST)
        model = self.panel.signal_list_widget.model()
        mime_data = model.mimeData([model.index(1, 0)])
        self.assertEqual(mime_data.text(), "speed")
        self.assertTrue(mime_data.hasFormat(
            self.panel_module.SIGNAL_MIME_TYPE_STR))
        self.assertIn(self.panel_module.SIGNAL_MIME_TYPE_STR,
                      model.mimeTypes())
        self.assertIn("text/plain", model.mimeTypes())

    @covers("LLFR-00021")
    def test_mime_type_literal(self) -> None:
        """The custom MIME type is the literal shared with plot widgets.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.panel_module.SIGNAL_MIME_TYPE_STR,
                         "application/x-plot-tool-signal")

    @covers("LLFR-00021")
    def test_list_is_drag_only_single_selection(self) -> None:
        """Items can be dragged out but not dropped in or reordered.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QAbstractItemView
        widget = self.panel.signal_list_widget
        self.assertEqual(widget.dragDropMode(),
                         QAbstractItemView.DragDropMode.DragOnly)
        self.assertTrue(widget.dragEnabled())
        self.assertFalse(widget.acceptDrops())
        self.assertEqual(widget.selectionMode(),
                         QAbstractItemView.SelectionMode.SingleSelection)
        self.panel.show_signal_names(NAME_LIST)
        self.assertTrue(widget.item(0).flags()
                        & Qt.ItemFlag.ItemIsDragEnabled)


if __name__ == "__main__":
    unittest.main()
