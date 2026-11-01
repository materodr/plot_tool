"""GUI tests: tabs never share a name (LLFR-00211, LLFR-00212).

They use a real MainWindow with the real controllers. The rename dialog
and the message box are patched, so no modal window is ever left open.
"""

import unittest
from unittest import mock

from tests.support import covers, get_qt_application, requires_qt


@requires_qt
class UniqueTabNameWindowTest(unittest.TestCase):
    """Rename through the tab menu and add tabs with the "+" button."""

    def setUp(self) -> None:
        """Create the window and the controllers, with two tabs.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from controller.main_controller import MainController
        from view.main_window import MainWindow
        self.main_window = MainWindow()
        self.controller = MainController(self.main_window)
        self.controller.start()
        self.plot_panel = self.main_window.plot_panel
        self.application.processEvents()
        self.click_add_tab()

    def tearDown(self) -> None:
        """Close the main window.

        Inputs: none.
        Outputs: none.
        """
        self.main_window.close()
        self.main_window.deleteLater()
        self.application.processEvents()

    def click_add_tab(self) -> None:
        """Click the "+" button with the mouse.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        QTest.mouseClick(self.plot_panel.add_tab_button,
                         Qt.MouseButton.LeftButton)
        self.application.processEvents()

    def rename_from_menu(self, tab_index_i: int, typed_name_str: str):
        """Choose "Rename" in a tab's menu and type a name.

        Inputs:
            tab_index_i: index of the tab.
            typed_name_str: the text the user types and accepts.
        Outputs: the list of the message boxes that were run.
        """
        from PyQt6.QtWidgets import QInputDialog, QMessageBox
        shown_box_list = []

        def fake_exec(box):
            """Record the box instead of showing it.

            Inputs:
                box: the QMessageBox whose exec was called.
            Outputs: the Ok button value.
            """
            shown_box_list.append(box)
            return QMessageBox.StandardButton.Ok.value

        menu = self.plot_panel.build_tab_menu(tab_index_i)
        rename_action = [action for action in menu.actions()
                         if action.text() == "Rename"][0]
        with mock.patch.object(QInputDialog, "getText",
                               return_value=(typed_name_str, True)), \
                mock.patch.object(QMessageBox, "exec", fake_exec):
            rename_action.trigger()
            self.application.processEvents()
        return shown_box_list

    @covers("LLFR-00211", "LLFR-00030", "HLFR-00017")
    def test_rename_to_another_tab_name_shows_box(self) -> None:
        """Renaming Tab 2 to " Tab 1 " keeps Tab 2 and shows the box.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QMessageBox
        self.assertEqual(self.main_window.tab_name_list(),
                         ["Tab 1", "Tab 2"])
        undo_history = self.controller.plot_controller.undo_history
        depth_i = undo_history.depth()
        shown_box_list = self.rename_from_menu(1, " Tab 1 ")
        self.assertEqual(len(shown_box_list), 1)
        shown_box = shown_box_list[0]
        self.assertEqual(shown_box.icon(), QMessageBox.Icon.Information)
        self.assertEqual(shown_box.windowTitle(), "Rename Tab")
        self.assertIn("'Tab 1'", shown_box.text())
        self.assertEqual(self.main_window.tab_name_list(),
                         ["Tab 1", "Tab 2"])
        # LLFR-00140: the refused rename records no undo step.
        self.assertEqual(undo_history.depth(), depth_i)

    @covers("LLFR-00211", "LLFR-00030", "HLFR-00017")
    def test_own_name_and_new_name_show_no_box(self) -> None:
        """The tab's own name and a free name are accepted silently.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.rename_from_menu(1, "Tab 2"), [])
        self.assertEqual(self.rename_from_menu(1, "tab 1"), [])
        self.assertEqual(self.main_window.tab_name_list(),
                         ["Tab 1", "tab 1"])

    @covers("LLFR-00212", "LLFR-00210", "LLFR-00026", "HLFR-00015")
    def test_add_tab_skips_a_renamed_tab_name(self) -> None:
        """With a tab renamed "Tab 3", the "+" button adds "Tab 4".

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(self.rename_from_menu(0, "Tab 3"), [])
        self.click_add_tab()
        self.click_add_tab()
        name_list = self.main_window.tab_name_list()
        self.assertEqual(name_list, ["Tab 3", "Tab 2", "Tab 4", "Tab 5"])
        self.assertEqual(len(set(name_list)), len(name_list))


if __name__ == "__main__":
    unittest.main()
