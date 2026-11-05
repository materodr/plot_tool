"""End-to-end tests of the PDF export and the copy (HLFR-00038, HLFR-00039).

A real MainWindow and MainController are used. The Export menu, the
save file dialog and the message boxes are patched, so no modal dialog
is ever left open.
"""

import os
import re
import tempfile
import unittest
from unittest import mock

from tests.support import button_name, covers, get_qt_application, requires_qt
from tests.support import OPEN_FILE_DIALOG_TARGET_STR

FILE_TEXT_STR = (
    "Time,speed,force\n"
    "0,0,1\n0.5,1,0\n1,2,-1\n1.5,3,0\n2,4,1\n")
# A PDF page object is "/Type /Page"; the page tree is "/Type /Pages".
PAGE_OBJECT_PATTERN_BYTES = rb"/Type\s*/Page(?![A-Za-z])"
SECOND_TAB_NAME_STR = "Second tab"


def pdf_page_count(path_str: str) -> int:
    """Return the number of pages of a PDF file.

    Inputs:
        path_str: path of the PDF file.
    Outputs: the number of page objects in the file.
    """
    with open(path_str, "rb") as pdf_file:
        content_bytes = pdf_file.read()
    return len(re.findall(PAGE_OBJECT_PATTERN_BYTES, content_bytes))


@requires_qt
class ExportCopyTest(unittest.TestCase):
    """Open a file, plot signals, then export and copy the plots."""

    def setUp(self) -> None:
        """Create a temp file, the main window and the controller.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from controller.main_controller import MainController
        from view.main_window import MainWindow
        self.message_box_class = QMessageBox
        self.file_dialog_class = QFileDialog
        self.temporary_folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_folder.cleanup)
        self.folder_str = self.temporary_folder.name
        data_path_str = os.path.join(self.folder_str, "data.csv")
        with open(data_path_str, "w", encoding="utf-8") as data_file:
            data_file.write(FILE_TEXT_STR)
        self.main_window = MainWindow()
        self.controller = MainController(self.main_window)
        self.controller.start()
        self.application.processEvents()
        self.box_record_list = []
        box_patch = mock.patch.object(
            QMessageBox, "exec", new=lambda box: self.fake_exec(box))
        box_patch.start()
        self.addCleanup(box_patch.stop)
        with mock.patch(OPEN_FILE_DIALOG_TARGET_STR,
                        return_value=data_path_str):
            self.controller.file_controller.open_file_requested()
        self.application.processEvents()
        self.top_panel = self.main_window.top_panel
        self.menu_text_list = []
        self.menu_choice_str = ""
        self.top_panel.execute_export_menu = self.fake_execute_menu

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
        Outputs: the int value of OK.
        """
        self.box_record_list.append(
            (box.windowTitle(), box.icon(), box.text()))
        return self.message_box_class.StandardButton.Ok.value

    def fake_execute_menu(self, menu):
        """Stand-in for the modal Export menu.

        Inputs:
            menu: the QMenu the Export button would show.
        Outputs: the action whose text is menu_choice_str, or None.
        """
        self.menu_text_list = [action.text() for action in menu.actions()]
        for action in menu.actions():
            if action.text() == self.menu_choice_str:
                return action
        return None

    def plot_signal(self, signal_name_str: str) -> None:
        """Plot a signal in a new plot of the current tab.

        Inputs:
            signal_name_str: name of the signal.
        Outputs: none.
        """
        self.main_window.signal_double_click_handler(signal_name_str)
        self.application.processEvents()

    def add_tab(self, name_str: str = "") -> int:
        """Add a tab, optionally rename it, and return its id.

        Inputs:
            name_str: new name of the tab, "" to keep the default name.
        Outputs: the id of the new (current) tab.
        """
        self.main_window.plot_panel.request_add_tab()
        self.application.processEvents()
        tab_id_i = self.main_window.current_tab_id()
        if name_str:
            self.controller.plot_controller.on_rename_tab(tab_id_i,
                                                          name_str)
        self.application.processEvents()
        return tab_id_i

    def click(self, button) -> None:
        """Click a top panel button and let its deferred action run.

        Inputs:
            button: the ToggleButton to click.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        for _ in range(3):
            self.application.processEvents()

    def export_to(self, answer_path_str: str):
        """Choose "Save all tabs as PDF" with a patched save dialog.

        Inputs:
            answer_path_str: the path the dialog returns ("" = cancel).
        Outputs: the mock of MainWindow.run_pdf_save_dialog.
        """
        self.menu_choice_str = "Save all tabs as PDF"
        with mock.patch.object(self.main_window, "run_pdf_save_dialog",
                               return_value=answer_path_str) as dialog_mock:
            self.click(self.top_panel.export_button)
        return dialog_mock

    def assert_plots_still_drawn(self, plot_widget_list: list) -> None:
        """Check that each plot's canvas still shows its plot on screen.

        Inputs:
            plot_widget_list: the PlotWidgets to check.
        Outputs: none.
        """
        import numpy as np
        self.application.processEvents()
        for plot_widget in plot_widget_list:
            canvas = plot_widget.canvas
            # The stored screen image has the screen size and is not
            # blank.
            buffer_array = np.asarray(canvas.buffer_rgba())
            self.assertEqual(buffer_array.shape[1],
                             int(round(plot_widget.figure.bbox.width)))
            self.assertEqual(buffer_array.shape[0],
                             int(round(plot_widget.figure.bbox.height)))
            colored_i = int((buffer_array[..., :3] < 250).any(-1).sum())
            self.assertGreater(colored_i, 0)
            # A repaint of the canvas shows the plot, not an empty area.
            image = canvas.grab().toImage()
            color_set = set()
            for x_i in range(0, image.width(), max(image.width() // 40, 1)):
                for y_i in range(0, image.height(),
                                 max(image.height() // 20, 1)):
                    color_set.add(image.pixel(x_i, y_i))
            self.assertGreater(len(color_set), 2)

    def tab_plot_widget_list(self, tab_id_i: int) -> list:
        """Return the PlotWidgets of a tab, from top to bottom.

        Inputs:
            tab_id_i: id of the tab.
        Outputs: a list of PlotWidget.
        """
        return [self.main_window.plot_view(plot_id_i) for plot_id_i in
                self.main_window.plot_panel.plot_id_list(tab_id_i)]

    def box_title_list(self) -> list:
        """Return the titles of the boxes shown so far.

        Inputs: none.
        Outputs: a list of str.
        """
        return [record[0] for record in self.box_record_list]

    # ----------------------------------------------------------------
    # Buttons and menu
    # ----------------------------------------------------------------

    @covers("LLFR-00126", "LLFR-00132", "LLFR-00001")
    def test_export_and_copy_buttons_exist(self) -> None:
        """The top panel has visible, inactive Export and Copy buttons.

        Inputs: none.
        Outputs: none.
        """
        from view.toggle_button import ToggleButton
        for button, text_str in ((self.top_panel.export_button, "Export"),
                                 (self.top_panel.copy_button, "Copy")):
            self.assertIsInstance(button, ToggleButton)
            self.assertEqual(button_name(button), text_str)
            self.assertTrue(button.isVisible())
            self.assertFalse(button.is_active())
            self.assertIs(button.parentWidget(), self.top_panel)
        self.assertLess(self.top_panel.export_button.x(),
                        self.top_panel.copy_button.x())

    @covers("LLFR-00127", "LLFR-01229", "HLFR-00038")
    def test_export_menu_has_pdf_option(self) -> None:
        """The Export menu holds "Save all tabs as PDF", then the Word
        and PNG options (LLFR-01229).

        Inputs: none.
        Outputs: none.
        """
        menu = self.top_panel.build_export_menu()
        self.assertEqual([action.text() for action in menu.actions()],
                         ["Save all tabs as PDF",
                          "Save all tabs as Word document (.docx)",
                          "Save each tab as PNG"])
        menu.deleteLater()

    @covers("LLFR-00127", "LLFR-00001", "LLFR-00003")
    def test_click_shows_menu_and_closed_menu_finishes(self) -> None:
        """A click shows the menu; closing it resets the button.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        self.menu_choice_str = ""
        QTest.mouseClick(self.top_panel.export_button,
                         Qt.MouseButton.LeftButton)
        # LLFR-00001: active once clicked, while the menu is pending.
        self.assertTrue(self.top_panel.export_button.is_active())
        for _ in range(3):
            self.application.processEvents()
        self.assertEqual(self.menu_text_list[0], "Save all tabs as PDF")
        self.assertFalse(self.top_panel.export_button.is_active())
        self.assertEqual(self.box_record_list, [])

    # ----------------------------------------------------------------
    # PDF export
    # ----------------------------------------------------------------

    @covers("LLFR-01230", "LLFR-01231", "LLFR-01232", "LLFR-00001",
            "LLFR-00003", "HLFR-00038")
    def test_word_export_writes_one_page_per_tab(self) -> None:
        """"Save all tabs as Word document (.docx)" shows a .docx save
        dialog and writes a Word document with one picture per tab.

        Inputs: none.
        Outputs: none.
        """
        import zipfile
        self.plot_signal("file1_speed")
        self.add_tab(SECOND_TAB_NAME_STR)
        self.plot_signal("file1_force")
        state_list = []

        def answer_dialog(dialog) -> str:
            """Record the dialog settings.

            Inputs:
                dialog: the QFileDialog that would be shown.
            Outputs: the chosen path without its extension.
            """
            state_list.append((dialog.acceptMode(), dialog.defaultSuffix(),
                               dialog.nameFilters()))
            return os.path.join(self.folder_str, "plots")

        self.menu_choice_str = "Save all tabs as Word document (.docx)"
        with mock.patch.object(self.main_window, "run_export_dialog",
                               side_effect=answer_dialog):
            self.click(self.top_panel.export_button)
        self.assertEqual(state_list, [
            (self.file_dialog_class.AcceptMode.AcceptSave, "docx",
             ["Word documents (*.docx)"])])
        path_str = os.path.join(self.folder_str, "plots.docx")
        with zipfile.ZipFile(path_str) as archive:
            document_str = archive.read("word/document.xml").decode()
            image_list = [name_str for name_str in archive.namelist()
                          if name_str.startswith("word/media/")]
            first_bytes = archive.read(image_list[0])
        self.assertEqual(len(image_list), 2)
        self.assertTrue(first_bytes.startswith(b"\x89PNG"))
        self.assertIn(SECOND_TAB_NAME_STR, document_str)
        self.assertIn("file1 = data.csv", document_str)
        self.assertEqual(self.box_record_list, [])
        self.assertFalse(self.top_panel.export_button.is_active())

    @covers("LLFR-01233", "LLFR-01234", "LLFR-01235", "LLFR-01236",
            "LLFR-01240",
            "HLFR-00038")
    def test_png_export_writes_one_file_per_tab(self) -> None:
        """"Save each tab as PNG" asks for a folder and writes one A4 page
        image per tab with a plot, named after the tab; an empty tab gets
        no file; a second export asks once before replacing.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtGui import QImage
        self.plot_signal("file1_speed")
        self.add_tab("a/b")
        self.plot_signal("file1_force")
        self.add_tab("empty")
        output_str = os.path.join(self.folder_str, "png")
        os.mkdir(output_str)
        self.menu_choice_str = "Save each tab as PNG"
        with mock.patch.object(self.main_window, "run_export_dialog",
                               return_value=output_str):
            self.click(self.top_panel.export_button)
        self.assertEqual(sorted(os.listdir(output_str)),
                         ["Tab 1.png", "a_b.png"])
        image = QImage(os.path.join(output_str, "a_b.png"))
        self.assertFalse(image.isNull())
        self.assertGreater(image.width(), image.height())
        self.assertEqual(self.box_record_list, [])
        with mock.patch.object(self.main_window, "run_export_dialog",
                               return_value=output_str):
            self.click(self.top_panel.export_button)
        self.assertEqual(self.box_title_list(), ["Replace Files"])
        self.assertIn("a_b.png", self.box_record_list[0][2])

    @covers("LLFR-00128", "LLFR-00129", "LLFR-00001", "LLFR-00003")
    def test_two_tabs_with_plots_give_two_pages(self) -> None:
        """Two tabs with plots give a two-page PDF at the chosen path.

        Inputs: none.
        Outputs: none.
        """
        self.plot_signal("file1_speed")
        self.plot_signal("file1_force")
        self.add_tab(SECOND_TAB_NAME_STR)
        self.plot_signal("file1_force")
        state_list = []

        def answer_dialog(dialog) -> str:
            """Record the dialog settings and the button state.

            Inputs:
                dialog: the QFileDialog that would be shown.
            Outputs: the chosen path without the .pdf extension.
            """
            state_list.append(
                (dialog.acceptMode(), dialog.defaultSuffix(),
                 dialog.nameFilters(),
                 self.top_panel.export_button.is_active()))
            return os.path.join(self.folder_str, "plots")

        self.menu_choice_str = "Save all tabs as PDF"
        with mock.patch.object(self.main_window, "run_pdf_save_dialog",
                               side_effect=answer_dialog):
            self.click(self.top_panel.export_button)
        # LLFR-00128: one save dialog for a .pdf file; LLFR-00001: the
        # button is active while it is shown.
        self.assertEqual(state_list, [
            (self.file_dialog_class.AcceptMode.AcceptSave, "pdf",
             ["PDF files (*.pdf)"], True)])
        path_str = os.path.join(self.folder_str, "plots.pdf")
        self.assertTrue(os.path.isfile(path_str))
        with open(path_str, "rb") as pdf_file:
            self.assertTrue(pdf_file.read().startswith(b"%PDF"))
        self.assertEqual(pdf_page_count(path_str), 2)
        self.assertEqual(self.box_record_list, [])
        # LLFR-00003: the button is back to normal.
        self.assertFalse(self.top_panel.export_button.is_active())

    @covers("LLFR-00128")
    def test_save_dialog_names_the_real_file(self) -> None:
        """The dialog saves, filters .pdf and adds the pdf suffix.

        Inputs: none.
        Outputs: none.
        """
        dialog = self.main_window.build_pdf_save_dialog()
        self.assertEqual(dialog.acceptMode(),
                         self.file_dialog_class.AcceptMode.AcceptSave)
        self.assertEqual(dialog.defaultSuffix(), "pdf")
        self.assertEqual(dialog.nameFilters(), ["PDF files (*.pdf)"])
        # Qt asks before overwriting: the option is not switched off.
        self.assertFalse(dialog.testOption(
            self.file_dialog_class.Option.DontConfirmOverwrite))
        dialog.deleteLater()

    @covers("LLFR-00129")
    def test_plots_are_sharp_on_the_page(self) -> None:
        """Each plot is drawn on the page at 200 dots per inch or more.

        Inputs: none.
        Outputs: none.
        """
        from view import plot_export
        self.plot_signal("file1_speed")
        self.plot_signal("file1_force")
        plot_widget_list = [
            self.main_window.plot_view(plot_id_i) for plot_id_i in
            self.main_window.plot_panel.plot_id_list(
                self.main_window.current_tab_id())]
        screen_dpi_list = [widget.figure.dpi for widget in plot_widget_list]
        drawn_list = []
        original_draw = plot_export.draw_page_image

        def recording_draw(*argument_tuple):
            """Draw the page and record the plot images it drew.

            Inputs:
                argument_tuple: the arguments of draw_page_image.
            Outputs: the list returned by draw_page_image.
            """
            result_list = original_draw(*argument_tuple)
            drawn_list.extend(result_list)
            return result_list

        with mock.patch.object(plot_export, "draw_page_image",
                               side_effect=recording_draw):
            self.export_to(os.path.join(self.folder_str, "sharp.pdf"))
        self.assertEqual(len(drawn_list), 2)
        for target_rect, plot_image in drawn_list:
            width_inches_f = (target_rect.width()
                              / plot_export.PDF_RESOLUTION_I)
            self.assertGreaterEqual(plot_image.width() / width_inches_f,
                                    200.0)
            height_inches_f = (target_rect.height()
                               / plot_export.PDF_RESOLUTION_I)
            self.assertGreaterEqual(plot_image.height() / height_inches_f,
                                    200.0)
            # The sharp image has the plot's on-screen aspect ratio.
            self.assertAlmostEqual(
                plot_image.width() / plot_image.height(),
                target_rect.width() / target_rect.height(), delta=0.05)
        # The plots on screen keep their resolution.
        self.assertEqual([widget.figure.dpi for widget in plot_widget_list],
                         screen_dpi_list)

    @covers("LLFR-00129")
    def test_plots_stay_drawn_after_export(self) -> None:
        """After an export, the plots of the current and of a hidden tab
        are still drawn on screen.

        Inputs: none.
        Outputs: none.
        """
        self.plot_signal("file1_speed")
        self.plot_signal("file1_force")
        first_tab_id_i = self.main_window.current_tab_id()
        second_tab_id_i = self.add_tab(SECOND_TAB_NAME_STR)
        self.plot_signal("file1_force")
        self.main_window.set_current_tab(first_tab_id_i)
        self.application.processEvents()
        path_str = os.path.join(self.folder_str, "drawn.pdf")
        self.export_to(path_str)
        self.assertTrue(os.path.isfile(path_str))
        self.assert_plots_still_drawn(
            self.tab_plot_widget_list(first_tab_id_i))
        # The hidden tab is checked where it was exported, then shown.
        self.assert_plots_still_drawn(
            self.tab_plot_widget_list(second_tab_id_i))
        self.main_window.set_current_tab(second_tab_id_i)
        self.assert_plots_still_drawn(
            self.tab_plot_widget_list(second_tab_id_i))

    @covers("LLFR-00129")
    def test_plots_stay_drawn_after_failed_render(self) -> None:
        """A failing high-resolution render still leaves the plot drawn.

        Inputs: none.
        Outputs: none.
        """
        from matplotlib.figure import Figure
        self.plot_signal("file1_speed")
        plot_widget_list = self.tab_plot_widget_list(
            self.main_window.current_tab_id())
        original_savefig = Figure.savefig

        def failing_savefig(figure, *argument_tuple, **argument_dict):
            """Render like savefig, then fail.

            Inputs:
                figure: the Figure being saved.
                argument_tuple: positional arguments of savefig.
                argument_dict: keyword arguments of savefig.
            Outputs: none. Raises RuntimeError.
            """
            original_savefig(figure, *argument_tuple, **argument_dict)
            raise RuntimeError("render failed")

        with mock.patch.object(Figure, "savefig", new=failing_savefig):
            with self.assertRaises(RuntimeError):
                self.main_window.save_tabs_pdf(
                    os.path.join(self.folder_str, "failed.pdf"))
        self.assert_plots_still_drawn(plot_widget_list)

    @covers("LLFR-00129")
    def test_page_plot_matches_screen_with_tips_and_markers(self) -> None:
        """The sharp plot on the page looks like the plot on screen, with
        a dragged pinned tip, its leader line and a vertical marker.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import qGray
        from view import plot_export
        self.plot_signal("file1_speed")
        plot_id_i = self.main_window.plot_panel.plot_id_list(
            self.main_window.current_tab_id())[0]
        plot_controller = self.controller.plot_controller
        plot_controller.on_tip_pin(plot_id_i, "file1_speed", 1.0, 2.0)
        plot_controller.on_pinned_tip_move(plot_id_i, 0, 60.0, -40.0)
        plot_controller.on_marker_place(plot_id_i, 1.5)
        self.application.processEvents()
        plot_widget = self.main_window.plot_view(plot_id_i)
        offset_tuple = tuple(plot_widget.pinned_annotation_list[0].xyann)
        drawn_list = []
        original_draw = plot_export.draw_page_image

        def recording_draw(*argument_tuple):
            """Draw the page and record the plot images it drew.

            Inputs:
                argument_tuple: the arguments of draw_page_image.
            Outputs: the list returned by draw_page_image.
            """
            result_list = original_draw(*argument_tuple)
            drawn_list.extend(result_list)
            return result_list

        with mock.patch.object(plot_export, "draw_page_image",
                               side_effect=recording_draw):
            self.export_to(os.path.join(self.folder_str, "tips.pdf"))
        self.application.processEvents()
        page_image = drawn_list[0][1]
        screen_image = plot_widget.canvas.grab().toImage()
        grid_width_i = 60
        grid_height_i = 30
        small_page = page_image.scaled(
            grid_width_i, grid_height_i,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation)
        small_screen = screen_image.scaled(
            grid_width_i, grid_height_i,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation)
        close_count_i = 0
        for x_i in range(grid_width_i):
            for y_i in range(grid_height_i):
                page_gray_i = qGray(small_page.pixel(x_i, y_i))
                screen_gray_i = qGray(small_screen.pixel(x_i, y_i))
                if abs(page_gray_i - screen_gray_i) <= 48:
                    close_count_i += 1
        self.assertGreaterEqual(close_count_i / (grid_width_i
                                                 * grid_height_i), 0.9)
        # The export does not move the dragged tip on screen.
        self.assertEqual(
            tuple(plot_widget.pinned_annotation_list[0].xyann),
            offset_tuple)

    @covers("LLFR-00129")
    def test_current_tab_restored_after_error(self) -> None:
        """The tab shown before the export is shown again after an error.

        Inputs: none.
        Outputs: none.
        """
        from view import plot_export
        self.plot_signal("file1_speed")
        first_tab_id_i = self.main_window.current_tab_id()
        self.add_tab(SECOND_TAB_NAME_STR)
        self.plot_signal("file1_force")
        self.main_window.set_current_tab(first_tab_id_i)
        self.application.processEvents()
        original_grab = plot_export.grab_page_image
        call_list = []

        def failing_grab(page):
            """Grab the first page, then fail on the second one.

            Inputs:
                page: the TabPage to grab.
            Outputs: the grabbed QImage for the first page.
            """
            call_list.append(page.name_str)
            if len(call_list) > 1:
                raise RuntimeError("grab failed")
            return original_grab(page)

        path_str = os.path.join(self.folder_str, "error.pdf")
        with mock.patch.object(plot_export, "grab_page_image",
                               side_effect=failing_grab):
            with self.assertRaises(RuntimeError):
                self.main_window.save_tabs_pdf(path_str)
        self.assertEqual(call_list, ["Tab 1", SECOND_TAB_NAME_STR])
        self.assertEqual(self.main_window.current_tab_id(), first_tab_id_i)
        self.assertFalse(os.path.exists(path_str))

    @covers("LLFR-00129")
    def test_empty_tab_gets_no_page(self) -> None:
        """A tab without plots is left out of the PDF.

        Inputs: none.
        Outputs: none.
        """
        self.plot_signal("file1_speed")
        self.add_tab(SECOND_TAB_NAME_STR)
        path_str = os.path.join(self.folder_str, "one.pdf")
        self.export_to(path_str)
        self.assertEqual(pdf_page_count(path_str), 1)

    @covers("LLFR-00129")
    def test_pages_have_tab_names_in_tab_order(self) -> None:
        """Each page starts with its tab's name, in tab order.

        Inputs: none.
        Outputs: none.
        """
        from view import plot_export
        self.plot_signal("file1_speed")
        self.add_tab("Empty tab")
        self.add_tab(SECOND_TAB_NAME_STR)
        self.plot_signal("file1_force")
        with mock.patch.object(plot_export, "draw_page_title",
                               wraps=plot_export.draw_page_title) as title:
            self.export_to(os.path.join(self.folder_str, "named.pdf"))
        drawn_name_list = [call.args[1] for call in title.call_args_list]
        self.assertEqual(drawn_name_list, ["Tab 1", SECOND_TAB_NAME_STR])

    @covers("LLFR-00129")
    def test_hidden_tab_is_drawn_like_visible_tab(self) -> None:
        """A tab that is not shown is drawn at the visible tab's size.

        Inputs: none.
        Outputs: none.
        """
        from view import plot_export
        self.plot_signal("file1_speed")
        first_tab_id_i = self.main_window.current_tab_id()
        self.add_tab(SECOND_TAB_NAME_STR)
        self.plot_signal("file1_force")
        self.plot_signal("file1_speed")
        # The first tab was never shown at its current size with plots.
        self.main_window.set_current_tab(first_tab_id_i)
        self.application.processEvents()
        visible_size = self.main_window.plot_panel.tab_widget \
            .currentWidget().size()
        with mock.patch.object(plot_export, "draw_page_image",
                               wraps=plot_export.draw_page_image) as draw:
            self.export_to(os.path.join(self.folder_str, "size.pdf"))
        image_list = [call.args[1] for call in draw.call_args_list]
        self.assertEqual(len(image_list), 2)
        for image in image_list:
            self.assertFalse(image.isNull())
            ratio_f = image.devicePixelRatio()
            self.assertAlmostEqual(image.width() / ratio_f,
                                   visible_size.width(), delta=1)
            self.assertAlmostEqual(image.height() / ratio_f,
                                   visible_size.height(), delta=1)
        # The tab the user was looking at is shown again.
        self.assertEqual(self.main_window.current_tab_id(), first_tab_id_i)

    @covers("LLFR-00129", "LLFR-00070")
    def test_hidden_tab_is_exported_at_the_shared_range(self) -> None:
        """A zoom in the shown tab is also on the page of a hidden tab.

        Inputs: none.
        Outputs: none.
        """
        from view import plot_export
        self.plot_signal("file1_speed")
        first_tab_id_i = self.main_window.current_tab_id()
        hidden_plot_id_i = self.main_window.plot_panel.plot_id_list(
            first_tab_id_i)[0]
        second_tab_id_i = self.add_tab(SECOND_TAB_NAME_STR)
        self.plot_signal("file1_force")
        shown_plot_id_i = self.main_window.plot_panel.plot_id_list(
            second_tab_id_i)[0]
        shown_widget = self.main_window.plot_view(shown_plot_id_i)
        shown_widget.wheel_at(shown_widget.data_to_widget_point(1.0, 0.0),
                              8.0)
        self.application.processEvents()
        zoomed_tuple = shown_widget.time_range_tuple()
        self.assertLess(zoomed_tuple[1] - zoomed_tuple[0], 2.0)
        hidden_widget = self.main_window.plot_view(hidden_plot_id_i)
        self.assertEqual(self.main_window.current_tab_id(), second_tab_id_i)
        self.assertFalse(hidden_widget.isVisible())
        rendered_range_list = []
        original_render = plot_export.render_figure_image

        def recording_render(figure, dpi_f: float):
            """Record the x range of a figure when it is rendered.

            Inputs:
                figure: the matplotlib Figure of a plot.
                dpi_f: dots per inch of the rendered image.
            Outputs: the image returned by render_figure_image.
            """
            rendered_range_list.append(
                (figure, tuple(figure.axes[0].get_xlim())))
            return original_render(figure, dpi_f)

        with mock.patch.object(plot_export, "render_figure_image",
                               side_effect=recording_render):
            self.export_to(os.path.join(self.folder_str, "zoom.pdf"))
        rendered_figure_list = [record_tuple[0]
                                for record_tuple in rendered_range_list]
        self.assertIn(hidden_widget.figure, rendered_figure_list)
        self.assertIn(shown_widget.figure, rendered_figure_list)
        for _, range_tuple in rendered_range_list:
            for index_i in range(2):
                self.assertAlmostEqual(range_tuple[index_i],
                                       zoomed_tuple[index_i])

    @covers("LLFR-00129")
    def test_page_image_shows_the_plot(self) -> None:
        """The image put on a page is the plot as drawn on screen.

        Inputs: none.
        Outputs: none.
        """
        from view import plot_export
        self.plot_signal("file1_speed")
        with mock.patch.object(plot_export, "draw_page_image",
                               wraps=plot_export.draw_page_image) as draw:
            self.export_to(os.path.join(self.folder_str, "look.pdf"))
        image = draw.call_args_list[0].args[1]
        # The image is not a blank page: it holds several colors.
        color_set = set()
        for x_i in range(0, image.width(), max(image.width() // 40, 1)):
            for y_i in range(0, image.height(),
                             max(image.height() // 40, 1)):
                color_set.add(image.pixel(x_i, y_i))
        self.assertGreater(len(color_set), 2)

    @covers("LLFR-00130", "LLFR-00003")
    def test_cancelled_dialog_saves_nothing(self) -> None:
        """Cancelling the save dialog writes no file and shows no box.

        Inputs: none.
        Outputs: none.
        """
        self.plot_signal("file1_speed")
        before_list = sorted(os.listdir(self.folder_str))
        dialog_mock = self.export_to("")
        dialog_mock.assert_called_once()
        self.assertEqual(sorted(os.listdir(self.folder_str)), before_list)
        self.assertEqual(self.box_record_list, [])
        self.assertFalse(self.top_panel.export_button.is_active())

    @covers("LLFR-00145", "LLFR-00003", "LLFR-00459")
    def test_no_plots_shows_information_without_dialog(self) -> None:
        """With no plot in any tab, an information box is shown.

        Inputs: none.
        Outputs: none.
        """
        self.add_tab(SECOND_TAB_NAME_STR)
        dialog_mock = self.export_to(os.path.join(self.folder_str, "x"))
        dialog_mock.assert_not_called()
        self.assertEqual(self.box_record_list, [
            ("Export", self.message_box_class.Icon.Information,
             "There are no plots to export.")])
        self.assertFalse(os.path.exists(
            os.path.join(self.folder_str, "x.pdf")))
        self.assertFalse(self.top_panel.export_button.is_active())

    @covers("LLFR-00131", "LLFR-00003")
    def test_missing_folder_shows_error(self) -> None:
        """A path in a missing folder shows the export error box.

        Inputs: none.
        Outputs: none.
        """
        self.plot_signal("file1_speed")
        path_str = os.path.join(self.folder_str, "missing", "plots.pdf")
        self.export_to(path_str)
        self.assertEqual(len(self.box_record_list), 1)
        title_str, icon, text_str = self.box_record_list[0]
        self.assertEqual(title_str, "Export Error")
        self.assertEqual(icon, self.message_box_class.Icon.Critical)
        self.assertTrue(text_str.startswith("The file could not be saved."))
        self.assertIn("plots.pdf", text_str)
        self.assertFalse(os.path.exists(path_str))
        self.assertFalse(self.top_panel.export_button.is_active())

    @covers("LLFR-00131")
    def test_path_that_is_a_folder_shows_error(self) -> None:
        """A path naming an existing folder shows the export error box.

        Inputs: none.
        Outputs: none.
        """
        self.plot_signal("file1_speed")
        folder_path_str = os.path.join(self.folder_str, "taken.pdf")
        os.mkdir(folder_path_str)
        self.export_to(folder_path_str)
        self.assertEqual(self.box_title_list(), ["Export Error"])
        self.assertTrue(os.path.isdir(folder_path_str))

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0,
                     "root may write read-only files")
    @covers("LLFR-00131")
    def test_read_only_file_survives_failed_export(self) -> None:
        """A read-only existing PDF is kept unchanged and an error shown.

        Inputs: none.
        Outputs: none.
        """
        self.plot_signal("file1_speed")
        path_str = os.path.join(self.folder_str, "report.pdf")
        with open(path_str, "wb") as existing_file:
            existing_file.write(b"old report")
        os.chmod(path_str, 0o444)
        self.addCleanup(os.chmod, path_str, 0o644)
        self.export_to(path_str)
        self.assertEqual(self.box_title_list(), ["Export Error"])
        self.assertTrue(self.box_record_list[0][2].startswith(
            "The file could not be saved."))
        with open(path_str, "rb") as existing_file:
            self.assertEqual(existing_file.read(), b"old report")
        self.assertEqual(sorted(os.listdir(self.folder_str)),
                         ["data.csv", "report.pdf"])
        self.assertFalse(self.top_panel.export_button.is_active())

    @covers("LLFR-00131")
    def test_failed_document_shows_error(self) -> None:
        """A PDF document that cannot be made shows the error box.

        Inputs: none.
        Outputs: none.
        """
        from view import plot_export
        self.plot_signal("file1_speed")
        path_str = os.path.join(self.folder_str, "broken.pdf")
        with mock.patch.object(plot_export, "build_pdf_bytes",
                               side_effect=OSError("no document")):
            self.export_to(path_str)
        self.assertEqual(self.box_title_list(), ["Export Error"])
        self.assertIn("no document", self.box_record_list[0][2])
        self.assertFalse(os.path.exists(path_str))

    # ----------------------------------------------------------------
    # Copy
    # ----------------------------------------------------------------

    @covers("LLFR-00133", "LLFR-00001", "LLFR-00003")
    def test_copy_puts_tab_image_on_clipboard(self) -> None:
        """Copy puts an image of the current tab on the clipboard.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QApplication
        from view import plot_export
        self.plot_signal("file1_speed")
        self.plot_signal("file1_force")
        clipboard = QApplication.clipboard()
        clipboard.setText("before")
        state_list = []
        original_grab = plot_export.grab_page_image

        def recording_grab(page):
            """Record the Copy button state, then grab the page.

            Inputs:
                page: the TabPage to grab.
            Outputs: the grabbed QImage.
            """
            state_list.append(self.top_panel.copy_button.is_active())
            return original_grab(page)

        with mock.patch.object(plot_export, "grab_page_image",
                               side_effect=recording_grab):
            self.click(self.top_panel.copy_button)
        self.assertEqual(state_list, [True])
        image = clipboard.image()
        self.assertFalse(image.isNull())
        page_size = self.main_window.plot_panel.tab_widget \
            .currentWidget().size()
        # LLFR-00972: the strip of the data files is above the plots.
        strip_i = plot_export.strip_height_px(
            "file1 = data.csv", float(page_size.width()))
        pixel_ratio_f = image.width() / page_size.width()
        plots_height_f = image.height() - strip_i * pixel_ratio_f
        self.assertAlmostEqual(image.width() / plots_height_f,
                               page_size.width() / page_size.height(),
                               delta=0.02)
        self.assertEqual(self.box_record_list, [])
        self.assertFalse(self.top_panel.copy_button.is_active())
        # The copied plots are still drawn on screen.
        self.assert_plots_still_drawn(self.tab_plot_widget_list(
            self.main_window.current_tab_id()))

    def open_second_file(self) -> None:
        """Open a second data file, run_B.csv, as file 2.

        Inputs: none.
        Outputs: none.
        """
        second_path_str = os.path.join(self.folder_str, "run_B.csv")
        with open(second_path_str, "w", encoding="utf-8") as data_file:
            data_file.write("Time,pressure\n0,1\n1,2\n2,3\n")
        with mock.patch(OPEN_FILE_DIALOG_TARGET_STR,
                        return_value=second_path_str):
            self.controller.file_controller.open_file_requested()
        self.application.processEvents()

    @covers("LLFR-00971", "LLFR-00129", "HLFR-00038", "HLFR-00113")
    def test_pages_describe_every_open_file(self) -> None:
        """Each page has the description of all files below the name.

        Inputs: none.
        Outputs: none.
        """
        from view import plot_export
        self.open_second_file()
        self.plot_signal("file1_speed")
        self.add_tab(SECOND_TAB_NAME_STR)
        self.plot_signal("file2_pressure")
        with mock.patch.object(
                plot_export, "draw_page_title",
                wraps=plot_export.draw_page_title) as title_mock, \
                mock.patch.object(
                    plot_export, "draw_page_description",
                    wraps=plot_export.draw_page_description) as text_mock, \
                mock.patch.object(
                    plot_export, "draw_page_image",
                    wraps=plot_export.draw_page_image) as image_mock:
            path_str = os.path.join(self.folder_str, "files.pdf")
            self.export_to(path_str)
        self.assertEqual(pdf_page_count(path_str), 2)
        # The description of ALL the open files on every page, even on
        # a page whose plots use only one of them.
        self.assertEqual([call.args[1] for call in text_mock.call_args_list],
                         ["file1 = data.csv, file2 = run_B.csv"] * 2)
        self.assertEqual(len(title_mock.call_args_list), 2)
        for page_index_i in range(2):
            # Directly below the tab's name: it starts where the name
            # ends, and the plots start below it.
            description_top_i = text_mock.call_args_list[
                page_index_i].args[2]
            self.assertGreater(description_top_i, 0)
            plots_top_i = image_mock.call_args_list[page_index_i].args[2]
            self.assertGreater(plots_top_i, description_top_i)
        self.assertEqual(self.box_record_list, [])

    @covers("LLFR-00972", "LLFR-00133", "HLFR-00039", "HLFR-00113")
    def test_copied_image_has_its_own_strip(self) -> None:
        """The strip is added above the plots and covers none of them.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtGui import QColor
        from PyQt6.QtWidgets import QApplication
        from view import plot_export
        self.open_second_file()
        self.plot_signal("file1_speed")
        grab_list = []
        original_grab = plot_export.grab_page_image

        def recording_grab(page):
            """Grab the page and keep the image.

            Inputs:
                page: the TabPage.
            Outputs: the QImage.
            """
            grab_list.append(original_grab(page))
            return grab_list[-1]

        with mock.patch.object(plot_export, "grab_page_image",
                               side_effect=recording_grab), \
                mock.patch.object(
                    plot_export, "image_with_description_strip",
                    wraps=plot_export.image_with_description_strip) as strip:
            self.click(self.top_panel.copy_button)
        self.assertEqual(strip.call_args.args[1],
                         "file1 = data.csv, file2 = run_B.csv")
        grabbed = grab_list[0]
        copied = QApplication.clipboard().image()
        self.assertEqual(copied.width(), grabbed.width())
        strip_device_i = copied.height() - grabbed.height()
        self.assertGreater(strip_device_i, 0)
        # The plots are whole below the strip: same pixels.
        for x_i in range(0, grabbed.width(), max(grabbed.width() // 15, 1)):
            for y_i in range(0, grabbed.height(),
                             max(grabbed.height() // 15, 1)):
                self.assertEqual(
                    QColor(copied.pixel(x_i, y_i + strip_device_i)).rgb(),
                    QColor(grabbed.pixel(x_i, y_i)).rgb())
        # The strip has the page's background at its corner and text.
        background_color, _ = plot_export.strip_colors(
            self.main_window.plot_panel.tab_widget.currentWidget())
        self.assertEqual(QColor(copied.pixel(1, 1)).rgb(),
                         background_color.rgb())
        strip_color_set = {
            QColor(copied.pixel(x_i, y_i)).rgb()
            for x_i in range(0, copied.width(), 2)
            for y_i in range(0, strip_device_i, 2)}
        self.assertGreater(len(strip_color_set), 1)

    @covers("LLFR-00146", "LLFR-00003", "LLFR-00460")
    def test_copy_without_plots_keeps_clipboard(self) -> None:
        """With no plot in the current tab, the clipboard is unchanged.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QApplication
        self.plot_signal("file1_speed")
        self.add_tab(SECOND_TAB_NAME_STR)
        clipboard = QApplication.clipboard()
        clipboard.setText("keep me")
        self.click(self.top_panel.copy_button)
        self.assertEqual(clipboard.text(), "keep me")
        self.assertTrue(clipboard.image().isNull())
        self.assertEqual(self.box_record_list, [
            ("Copy", self.message_box_class.Icon.Information,
             "There are no plots to copy.")])
        self.assertFalse(self.top_panel.copy_button.is_active())


@requires_qt
class ExportBoxTest(unittest.TestCase):
    """Check the boxes of the export and the copy."""

    def setUp(self) -> None:
        """Start the Qt application.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()

    @covers("LLFR-00131")
    def test_export_error_box(self) -> None:
        """The export error box is critical and gives the reason.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QMessageBox
        from view import message_boxes
        box = message_boxes.build_export_error_box(None, "Disk full")
        self.assertEqual(box.icon(), QMessageBox.Icon.Critical)
        self.assertEqual(box.windowTitle(), "Export Error")
        self.assertEqual(box.text(),
                         "The file could not be saved.\n\nDisk full")
        box.deleteLater()

    @covers("LLFR-00145", "LLFR-00146")
    def test_information_boxes(self) -> None:
        """The nothing-to-export and nothing-to-copy boxes inform.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtWidgets import QMessageBox
        from view import message_boxes
        export_box = message_boxes.build_nothing_to_export_box(None)
        copy_box = message_boxes.build_nothing_to_copy_box(None)
        self.assertEqual(export_box.icon(), QMessageBox.Icon.Information)
        self.assertEqual(export_box.text(), "There are no plots to export.")
        self.assertEqual(copy_box.icon(), QMessageBox.Icon.Information)
        self.assertEqual(copy_box.text(), "There are no plots to copy.")
        export_box.deleteLater()
        copy_box.deleteLater()


@requires_qt
class DescriptionDrawingTest(unittest.TestCase):
    """The drawing of the description, on images (LLFR-00971/00972)."""

    def setUp(self) -> None:
        """Start Qt.

        Inputs: none.
        Outputs: none.
        """
        self.application = get_qt_application()

    @covers("LLFR-00972", "LLFR-00133")
    def test_strip_is_added_above_the_image(self) -> None:
        """A red image keeps its pixels below a strip of the background.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtGui import QColor, QImage
        from view import plot_export
        image = QImage(200, 60, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(QColor("#ff0000"))
        white, black = QColor("#ffffff"), QColor("#000000")
        result = plot_export.image_with_description_strip(
            image, "file1 = run_A.csv, file2 = run_B.mat", white, black)
        strip_i = plot_export.strip_height_px(
            "file1 = run_A.csv, file2 = run_B.mat", 200.0)
        self.assertEqual(result.width(), 200)
        self.assertEqual(result.height(), 60 + strip_i)
        self.assertEqual(QColor(result.pixel(0, 0)).rgb(), white.rgb())
        for y_i in (strip_i, strip_i + 30, strip_i + 59):
            self.assertEqual(QColor(result.pixel(100, y_i)).rgb(),
                             QColor("#ff0000").rgb())
        dark_found_b = any(
            QColor(result.pixel(x_i, y_i)).lightness() < 128
            for x_i in range(200) for y_i in range(strip_i))
        self.assertTrue(dark_found_b)
        # No description, no strip.
        self.assertIs(plot_export.image_with_description_strip(
            image, "", white, black), image)
        self.assertEqual(plot_export.strip_height_px("", 200.0), 0)

    @covers("LLFR-00972", "LLFR-00971")
    def test_long_description_wraps_into_a_higher_strip(self) -> None:
        """Ten files in a narrow image take several lines, none cut.

        Inputs: none.
        Outputs: none.
        """
        from view import plot_export
        long_str = ", ".join(f"file{number_i} = measurement_{number_i}.csv"
                             for number_i in range(1, 11))
        self.assertGreater(plot_export.strip_height_px(long_str, 300.0),
                           2 * plot_export.strip_height_px("file1 = a.csv",
                                                           300.0))

    @covers("LLFR-00971", "LLFR-00129")
    def test_page_description_height(self) -> None:
        """The description takes room on a page, more when it wraps.

        Inputs: none.
        Outputs: none.
        """
        from PyQt6.QtGui import QColor, QImage, QPainter
        from view import plot_export
        image = QImage(600, 400, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(QColor("#ffffff"))
        painter = QPainter(image)
        try:
            self.assertEqual(plot_export.draw_page_description(
                painter, "", 10, 600), 0)
            short_i = plot_export.draw_page_description(
                painter, "file1 = run_A.csv", 10, 600)
            long_str = ", ".join(f"file{number_i} = run_{number_i}.csv"
                                 for number_i in range(1, 11))
            long_i = plot_export.draw_page_description(
                painter, long_str, 100, 200)
        finally:
            painter.end()
        self.assertGreater(short_i, 0)
        self.assertGreater(long_i, short_i)
        # The text was drawn below the given top.
        self.assertTrue(any(QColor(image.pixel(x_i, y_i)).lightness() < 128
                            for x_i in range(600) for y_i in range(10, 40)))
        self.assertTrue(all(QColor(image.pixel(x_i, 5)).lightness() > 250
                            for x_i in range(600)))


if __name__ == "__main__":
    unittest.main()
