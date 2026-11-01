"""Tests for the safe file writing of the export (no Qt needed)."""

import errno
import os
import stat
import tempfile
import unittest
from unittest import mock

from tests.support import covers

from view import file_writing

OLD_CONTENT_BYTES = b"old report"
NEW_CONTENT_BYTES = b"%PDF-1.4 new report"


def running_as_root_b() -> bool:
    """Tell whether the tests run as the root user.

    Inputs: none.
    Outputs: True for root, who may write read-only files.
    """
    return hasattr(os, "geteuid") and os.geteuid() == 0


class WriteFileSafelyTest(unittest.TestCase):
    """Check that a failed write never damages the existing file."""

    def setUp(self) -> None:
        """Create an empty temporary folder.

        Inputs: none.
        Outputs: none.
        """
        self.temporary_folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_folder.cleanup)
        self.folder_str = self.temporary_folder.name
        self.path_str = os.path.join(self.folder_str, "report.pdf")

    def write_existing_file(self) -> None:
        """Create report.pdf with the old content.

        Inputs: none.
        Outputs: none.
        """
        with open(self.path_str, "wb") as existing_file:
            existing_file.write(OLD_CONTENT_BYTES)

    def read_target(self) -> bytes:
        """Return the content of report.pdf.

        Inputs: none.
        Outputs: the bytes of the file.
        """
        with open(self.path_str, "rb") as target_file:
            return target_file.read()

    def assert_only_target_left(self, expected_list: list) -> None:
        """Check the folder holds exactly the expected names (no temp).

        Inputs:
            expected_list: the file names that must be in the folder.
        Outputs: none.
        """
        self.assertEqual(sorted(os.listdir(self.folder_str)),
                         sorted(expected_list))

    @covers("LLFR-00131")
    def test_new_file_is_written(self) -> None:
        """A new file gets the content and the usual permissions.

        Inputs: none.
        Outputs: none.
        """
        written_b, reason_str = file_writing.write_file_safely(
            self.path_str, NEW_CONTENT_BYTES)
        self.assertTrue(written_b)
        self.assertEqual(reason_str, "")
        self.assertEqual(self.read_target(), NEW_CONTENT_BYTES)
        self.assert_only_target_left(["report.pdf"])
        mode_i = stat.S_IMODE(os.stat(self.path_str).st_mode)
        self.assertEqual(mode_i, 0o666 & ~file_writing.current_umask_i())

    @covers("LLFR-00131")
    def test_existing_file_is_replaced_with_its_mode(self) -> None:
        """A writable existing file is replaced and keeps its mode.

        Inputs: none.
        Outputs: none.
        """
        self.write_existing_file()
        os.chmod(self.path_str, 0o640)
        written_b, _ = file_writing.write_file_safely(self.path_str,
                                                      NEW_CONTENT_BYTES)
        self.assertTrue(written_b)
        self.assertEqual(self.read_target(), NEW_CONTENT_BYTES)
        self.assertEqual(stat.S_IMODE(os.stat(self.path_str).st_mode),
                         0o640)
        self.assert_only_target_left(["report.pdf"])

    @unittest.skipIf(running_as_root_b(), "root may write read-only files")
    @covers("LLFR-00131")
    def test_read_only_file_survives(self) -> None:
        """A read-only existing file is refused and left unchanged.

        Inputs: none.
        Outputs: none.
        """
        self.write_existing_file()
        os.chmod(self.path_str, 0o444)
        self.addCleanup(os.chmod, self.path_str, 0o644)
        written_b, reason_str = file_writing.write_file_safely(
            self.path_str, NEW_CONTENT_BYTES)
        self.assertFalse(written_b)
        self.assertIn(os.strerror(errno.EACCES), reason_str)
        self.assertIn(self.path_str, reason_str)
        self.assertEqual(self.read_target(), OLD_CONTENT_BYTES)
        self.assert_only_target_left(["report.pdf"])

    @covers("LLFR-00131")
    def test_missing_folder_is_reported(self) -> None:
        """A path in a missing folder is reported with the path.

        Inputs: none.
        Outputs: none.
        """
        path_str = os.path.join(self.folder_str, "missing", "report.pdf")
        written_b, reason_str = file_writing.write_file_safely(
            path_str, NEW_CONTENT_BYTES)
        self.assertFalse(written_b)
        self.assertIn(path_str, reason_str)
        self.assertFalse(os.path.exists(path_str))

    @covers("LLFR-00131")
    def test_folder_target_is_refused(self) -> None:
        """A path naming a folder is refused and the folder is kept.

        Inputs: none.
        Outputs: none.
        """
        os.mkdir(self.path_str)
        written_b, reason_str = file_writing.write_file_safely(
            self.path_str, NEW_CONTENT_BYTES)
        self.assertFalse(written_b)
        self.assertIn(os.strerror(errno.EISDIR), reason_str)
        self.assertTrue(os.path.isdir(self.path_str))
        self.assert_only_target_left(["report.pdf"])

    @covers("LLFR-00131")
    def test_full_disk_keeps_old_file_and_removes_temp(self) -> None:
        """A write that fails half way leaves the old file and no temp.

        Inputs: none.
        Outputs: none.
        """
        self.write_existing_file()

        def fail_half_way(output_file, content_bytes: bytes) -> None:
            """Write half of the bytes, then fail like a full disk.

            Inputs:
                output_file: the open temporary file.
                content_bytes: the bytes that should be written.
            Outputs: none. Raises OSError(ENOSPC).
            """
            output_file.write(content_bytes[:len(content_bytes) // 2])
            raise OSError(errno.ENOSPC, os.strerror(errno.ENOSPC))

        with mock.patch.object(file_writing, "write_content",
                               side_effect=fail_half_way):
            written_b, reason_str = file_writing.write_file_safely(
                self.path_str, NEW_CONTENT_BYTES)
        self.assertFalse(written_b)
        self.assertIn(os.strerror(errno.ENOSPC), reason_str)
        self.assertEqual(self.read_target(), OLD_CONTENT_BYTES)
        self.assert_only_target_left(["report.pdf"])

    @covers("LLFR-00131")
    def test_short_write_is_a_failure(self) -> None:
        """A write that silently stops short is reported, temp removed.

        Inputs: none.
        Outputs: none.
        """

        def write_half(output_file, content_bytes: bytes) -> None:
            """Write only half of the bytes without an error.

            Inputs:
                output_file: the open temporary file.
                content_bytes: the bytes that should be written.
            Outputs: none.
            """
            output_file.write(content_bytes[:len(content_bytes) // 2])

        with mock.patch.object(file_writing, "write_content",
                               side_effect=write_half):
            written_b, reason_str = file_writing.write_file_safely(
                self.path_str, NEW_CONTENT_BYTES)
        self.assertFalse(written_b)
        self.assertIn(file_writing.INCOMPLETE_WRITE_REASON_STR, reason_str)
        self.assert_only_target_left([])

    @covers("LLFR-00131")
    def test_failed_replace_keeps_old_file(self) -> None:
        """A failed final move keeps the old file and removes the temp.

        Inputs: none.
        Outputs: none.
        """
        self.write_existing_file()
        with mock.patch.object(file_writing.os, "replace",
                               side_effect=OSError(errno.EIO, "I/O error")):
            written_b, _ = file_writing.write_file_safely(
                self.path_str, NEW_CONTENT_BYTES)
        self.assertFalse(written_b)
        self.assertEqual(self.read_target(), OLD_CONTENT_BYTES)
        self.assert_only_target_left(["report.pdf"])

    @covers("LLFR-00131")
    def test_empty_content_is_refused(self) -> None:
        """Nothing is written for empty content.

        Inputs: none.
        Outputs: none.
        """
        written_b, _ = file_writing.write_file_safely(self.path_str, b"")
        self.assertFalse(written_b)
        self.assert_only_target_left([])


if __name__ == "__main__":
    unittest.main()
