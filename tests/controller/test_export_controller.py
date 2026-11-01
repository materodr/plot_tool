"""Tests for the export controller with a fake view (no Qt needed)."""

import unittest

from tests.support import covers

from controller.export_controller import ExportController, ensure_pdf_suffix


class FakeExportView:
    """Stand-in for MainWindow that records the export calls.

    Inputs: none.
    Attributes:
        exportable_tab_count_i: value returned by exportable_tab_count.
        current_plot_count_i: value returned by current_tab_plot_count.
        answer_path_str: path returned by the save file dialog.
        save_result_tuple: value returned by save_tabs_pdf.
        copy_result_tuple: value returned by copy_current_tab_image.
        call_list: names (and arguments) of the facade calls, in order.
    """

    def __init__(self) -> None:
        """Start with one tab with a plot and successful results.

        Inputs: none.
        Outputs: none.
        """
        self.exportable_tab_count_i = 1
        self.current_plot_count_i = 1
        self.answer_path_str = "/folder/plots.pdf"
        self.save_result_tuple = (True, "")
        self.copy_result_tuple = (True, "")
        self.save_error = None
        self.call_list = []

    def exportable_tab_count(self) -> int:
        """Return the number of tabs that hold a plot.

        Inputs: none.
        Outputs: exportable_tab_count_i.
        """
        self.call_list.append("exportable_tab_count")
        return self.exportable_tab_count_i

    def current_tab_plot_count(self) -> int:
        """Return the number of plots in the current tab.

        Inputs: none.
        Outputs: current_plot_count_i.
        """
        self.call_list.append("current_tab_plot_count")
        return self.current_plot_count_i

    def ask_pdf_save_path(self) -> str:
        """Record the dialog and return the prepared answer.

        Inputs: none.
        Outputs: answer_path_str.
        """
        self.call_list.append("ask_pdf_save_path")
        return self.answer_path_str

    def save_tabs_pdf(self, path_str: str) -> tuple:
        """Record the save and return the prepared result.

        Inputs:
            path_str: the path to save to.
        Outputs: save_result_tuple. Raises save_error when it is set.
        """
        self.call_list.append(("save_tabs_pdf", path_str))
        if self.save_error is not None:
            raise self.save_error
        return self.save_result_tuple

    def copy_current_tab_image(self) -> tuple:
        """Record the copy and return the prepared result.

        Inputs: none.
        Outputs: copy_result_tuple.
        """
        self.call_list.append("copy_current_tab_image")
        return self.copy_result_tuple

    def show_nothing_to_export(self) -> None:
        """Record the information box.

        Inputs: none.
        Outputs: none.
        """
        self.call_list.append("show_nothing_to_export")

    def show_nothing_to_copy(self) -> None:
        """Record the information box.

        Inputs: none.
        Outputs: none.
        """
        self.call_list.append("show_nothing_to_copy")

    def show_export_error(self, reason_str: str) -> None:
        """Record the error box.

        Inputs:
            reason_str: the reason shown.
        Outputs: none.
        """
        self.call_list.append(("show_export_error", reason_str))

    def show_copy_error(self, reason_str: str) -> None:
        """Record the error box.

        Inputs:
            reason_str: the reason shown.
        Outputs: none.
        """
        self.call_list.append(("show_copy_error", reason_str))

    def finish_export_button(self) -> None:
        """Record that the Export button returned to normal.

        Inputs: none.
        Outputs: none.
        """
        self.call_list.append("finish_export_button")

    def finish_copy_button(self) -> None:
        """Record that the Copy button returned to normal.

        Inputs: none.
        Outputs: none.
        """
        self.call_list.append("finish_copy_button")

    def called_names_list(self) -> list:
        """Return the names of the calls, without their arguments.

        Inputs: none.
        Outputs: a list of str.
        """
        return [call if isinstance(call, str) else call[0]
                for call in self.call_list]


class EnsurePdfSuffixTest(unittest.TestCase):
    """Check the .pdf extension of the chosen path."""

    @covers("LLFR-00128")
    def test_suffix_is_added_when_missing(self) -> None:
        """A path without .pdf gets it; one with .pdf is kept.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(ensure_pdf_suffix("/a/plots"), "/a/plots.pdf")
        self.assertEqual(ensure_pdf_suffix("/a/plots.txt"),
                         "/a/plots.txt.pdf")
        self.assertEqual(ensure_pdf_suffix("/a/plots.pdf"), "/a/plots.pdf")
        self.assertEqual(ensure_pdf_suffix("/a/plots.PDF"), "/a/plots.PDF")


class ExportFlowTest(unittest.TestCase):
    """Check the "Save all tabs as PDF" flow."""

    def setUp(self) -> None:
        """Create the controller with a fake view.

        Inputs: none.
        Outputs: none.
        """
        self.view = FakeExportView()
        self.controller = ExportController(self.view)

    @covers("LLFR-00128", "LLFR-00129", "LLFR-00003")
    def test_export_asks_path_and_saves(self) -> None:
        """With plots, the dialog is shown and the PDF is saved there.

        Inputs: none.
        Outputs: none.
        """
        self.controller.on_export_requested()
        self.assertEqual(self.view.call_list, [
            "exportable_tab_count", "ask_pdf_save_path",
            ("save_tabs_pdf", "/folder/plots.pdf"),
            "finish_export_button"])

    @covers("LLFR-00128")
    def test_export_adds_pdf_suffix(self) -> None:
        """A path typed without .pdf is saved with .pdf added.

        Inputs: none.
        Outputs: none.
        """
        self.view.answer_path_str = "/folder/report"
        self.controller.on_export_requested()
        self.assertIn(("save_tabs_pdf", "/folder/report.pdf"),
                      self.view.call_list)

    @covers("LLFR-00130", "LLFR-00003")
    def test_cancelled_dialog_saves_nothing(self) -> None:
        """A cancelled dialog saves nothing and shows no box.

        Inputs: none.
        Outputs: none.
        """
        self.view.answer_path_str = ""
        self.controller.on_export_requested()
        self.assertEqual(self.view.call_list, [
            "exportable_tab_count", "ask_pdf_save_path",
            "finish_export_button"])

    @covers("LLFR-00131", "LLFR-00003")
    def test_failed_save_shows_error_with_reason(self) -> None:
        """A failed write shows the export error box with the reason.

        Inputs: none.
        Outputs: none.
        """
        self.view.save_result_tuple = (False, "Permission denied")
        self.controller.on_export_requested()
        self.assertEqual(self.view.call_list[-2:], [
            ("show_export_error", "Permission denied"),
            "finish_export_button"])

    @covers("LLFR-00131")
    def test_successful_save_shows_no_error(self) -> None:
        """A successful save shows no error box.

        Inputs: none.
        Outputs: none.
        """
        self.controller.on_export_requested()
        self.assertNotIn("show_export_error",
                         self.view.called_names_list())

    @covers("LLFR-00145", "LLFR-00003")
    def test_no_plots_shows_information_and_no_dialog(self) -> None:
        """With no plot in any tab, only the information box is shown.

        Inputs: none.
        Outputs: none.
        """
        self.view.exportable_tab_count_i = 0
        self.controller.on_export_requested()
        self.assertEqual(self.view.call_list, [
            "exportable_tab_count", "show_nothing_to_export",
            "finish_export_button"])
        self.assertNotIn("ask_pdf_save_path", self.view.call_list)
        self.assertNotIn("save_tabs_pdf", self.view.called_names_list())

    @covers("LLFR-00003")
    def test_button_finishes_after_unexpected_error(self) -> None:
        """The Export button returns to normal even if saving raises.

        Inputs: none.
        Outputs: none.
        """
        self.view.save_error = RuntimeError("boom")
        with self.assertRaises(RuntimeError):
            self.controller.on_export_requested()
        self.assertEqual(self.view.call_list[-1], "finish_export_button")


class CopyFlowTest(unittest.TestCase):
    """Check the Copy flow."""

    def setUp(self) -> None:
        """Create the controller with a fake view.

        Inputs: none.
        Outputs: none.
        """
        self.view = FakeExportView()
        self.controller = ExportController(self.view)

    @covers("LLFR-00133", "LLFR-00003")
    def test_copy_with_plots_copies(self) -> None:
        """With plots in the current tab, the image is copied.

        Inputs: none.
        Outputs: none.
        """
        self.controller.on_copy_requested()
        self.assertEqual(self.view.call_list, [
            "current_tab_plot_count", "copy_current_tab_image",
            "finish_copy_button"])

    @covers("LLFR-00146", "LLFR-00003")
    def test_copy_without_plots_shows_information(self) -> None:
        """With no plot in the current tab, nothing is copied.

        Inputs: none.
        Outputs: none.
        """
        self.view.current_plot_count_i = 0
        self.controller.on_copy_requested()
        self.assertEqual(self.view.call_list, [
            "current_tab_plot_count", "show_nothing_to_copy",
            "finish_copy_button"])

    @covers("LLFR-00133")
    def test_failed_copy_shows_error(self) -> None:
        """A failed copy shows the copy error box.

        Inputs: none.
        Outputs: none.
        """
        self.view.copy_result_tuple = (False, "no image")
        self.controller.on_copy_requested()
        self.assertIn(("show_copy_error", "no image"), self.view.call_list)
        self.assertEqual(self.view.call_list[-1], "finish_copy_button")


if __name__ == "__main__":
    unittest.main()
