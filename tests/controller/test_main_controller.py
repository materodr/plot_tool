"""Tests for the main controller with a fake view (no Qt needed)."""

import unittest

from tests.support import covers

from tests.controller.test_plot_controller import FakePlotView

from controller.main_controller import MainController


class FakeMainWindow(FakePlotView):
    """Stand-in for MainWindow that records whether it was shown."""

    def __init__(self) -> None:
        """Start as not shown, with the plot-panel fake facade.

        Inputs: none.
        Outputs: none.
        """
        super().__init__()
        self.shown_b = False
        self.open_file_handler = None
        self.search_text_handler = None
        self.export_handler_tuple = ()

    def set_export_handlers(self, pdf_export_handler,
                            copy_handler) -> None:
        """Record the handlers of the Export menu and the Copy button.

        Inputs:
            pdf_export_handler: called for "Save all tabs as PDF".
            copy_handler: called when Copy is clicked.
        Outputs: none.
        """
        self.export_handler_tuple = (pdf_export_handler, copy_handler)

    def set_open_file_handler(self, handler) -> None:
        """Record the handler of the Open file button.

        Inputs:
            handler: the function called when Open file is clicked.
        Outputs: none.
        """
        self.open_file_handler = handler

    def set_search_text_handler(self, handler) -> None:
        """Record the handler of the search box.

        Inputs:
            handler: the function called with the new search text.
        Outputs: none.
        """
        self.search_text_handler = handler

    def set_synthetic_operation_groups(self, group_list: list) -> None:
        """Record the operation groups of the signal list menu.

        Inputs:
            group_list: (group label, [(operation id, label)]) tuples.
        Outputs: none.
        """
        self.operation_group_list = list(group_list)

    def set_signal_menu_handlers(self, *handler_tuple) -> None:
        """Record the handlers of the signal list menu.

        Inputs:
            handler_tuple: the create, copy name, rename, delete and
                copy equation handlers.
        Outputs: none.
        """
        self.signal_menu_handler_tuple = handler_tuple

    def set_layout_handlers(self, save_handler, load_handler) -> None:
        """Record the handlers of the Save and Load layout buttons.

        Inputs:
            save_handler: called when Save layout is clicked.
            load_handler: called when Load layout is clicked.
        Outputs: none.
        """
        self.layout_handler_tuple = (save_handler, load_handler)

    def set_layout_buttons_enabled(self, enabled_b: bool) -> None:
        """Record whether the layout buttons are enabled.

        Inputs:
            enabled_b: True when they are enabled.
        Outputs: none.
        """
        self.layout_buttons_enabled_b = bool(enabled_b)

    def show(self) -> None:
        """Record that the window was shown.

        Inputs: none.
        Outputs: none.
        """
        self.shown_b = True


class MainControllerStartTest(unittest.TestCase):
    """Check that starting the controller shows the window."""

    @covers("LLFR-00058")
    def test_start_shows_main_window(self) -> None:
        """start() shows the main window with its panels.

        Inputs: none.
        Outputs: none.
        """
        fake_window = FakeMainWindow()
        MainController(fake_window).start()
        self.assertTrue(fake_window.shown_b)

    @covers("LLFR-00005")
    def test_open_file_button_runs_file_controller(self) -> None:
        """The Open file handler is the file controller's flow.

        Inputs: none.
        Outputs: none.
        """
        fake_window = FakeMainWindow()
        controller = MainController(fake_window)
        self.assertEqual(fake_window.open_file_handler,
                         controller.file_controller.open_file_requested)
        self.assertIs(controller.file_controller.view, fake_window)

    @covers("LLFR-00015", "LLFR-00019", "LLFR-00024")
    def test_plot_controller_is_wired(self) -> None:
        """The plot controller listens to files and to the view.

        Inputs: none.
        Outputs: none.
        """
        fake_window = FakeMainWindow()
        controller = MainController(fake_window)
        plot_controller = controller.plot_controller
        self.assertIs(plot_controller.view, fake_window)
        self.assertIn(plot_controller.on_file_opened,
                      controller.file_controller.file_opened_listener_list)
        self.assertEqual(fake_window.handler_dict["double_click"],
                         plot_controller.on_signal_double_clicked)
        self.assertEqual(fake_window.handler_dict["plot_tool"],
                         plot_controller.on_plot_tool_changed)
        self.assertEqual(list(fake_window.tab_dict.values()), ["Tab 1"])

    @covers("LLFR-00095", "LLFR-00104")
    def test_signal_list_controller_is_wired(self) -> None:
        """The search box handler and the file listener are connected.

        Inputs: none.
        Outputs: none.
        """
        fake_window = FakeMainWindow()
        controller = MainController(fake_window)
        signal_list_controller = controller.signal_list_controller
        self.assertIs(signal_list_controller.view, fake_window)
        self.assertEqual(fake_window.search_text_handler,
                         signal_list_controller.on_search_text_changed)
        listener_list = controller.file_controller.file_opened_listener_list
        self.assertIn(signal_list_controller.on_file_opened, listener_list)
        # LLFR-00017: the search listener runs after the plot listener,
        # so it gives the final signal list of a new file.
        self.assertGreater(
            listener_list.index(signal_list_controller.on_file_opened),
            listener_list.index(controller.plot_controller.on_file_opened))

    @covers("LLFR-00128", "LLFR-00133")
    def test_export_controller_is_wired(self) -> None:
        """The Export menu and Copy button run the export controller.

        Inputs: none.
        Outputs: none.
        """
        fake_window = FakeMainWindow()
        controller = MainController(fake_window)
        export_controller = controller.export_controller
        self.assertIs(export_controller.view, fake_window)
        self.assertEqual(fake_window.export_handler_tuple,
                         (export_controller.on_export_requested,
                          export_controller.on_copy_requested))


if __name__ == "__main__":
    unittest.main()
