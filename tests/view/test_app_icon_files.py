"""Tests for the icon files of the standalone executable (LLFR-00182).

The packing of .icns and .ico files is checked without Qt; drawing the
real files needs PyQt6 and runs in CI.
"""

import os
import struct
import tempfile
import unittest

from tests.support import covers, get_qt_application, requires_qt

from view import app_icon_files


def fake_png_dict(size_tuple: tuple) -> dict:
    """Return distinct placeholder bytes for each size.

    Inputs:
        size_tuple: the sizes in pixels.
    Outputs: a dict size -> bytes that name the size.
    """
    return {size_i: f"png-{size_i}".encode("ascii") * 3
            for size_i in size_tuple}


class IconContainerTest(unittest.TestCase):
    """The .icns and .ico containers, packed in Python."""

    @covers("LLFR-00182")
    def test_icns_holds_every_standard_size(self) -> None:
        """The .icns has the header, one entry per type, the PNG data.

        Inputs: none.
        Outputs: none.
        """
        size_tuple = (16, 32, 64, 128, 256, 512, 1024)
        png_dict = fake_png_dict(size_tuple)
        icns_bytes = app_icon_files.pack_icns(png_dict)
        self.assertEqual(icns_bytes[:4], b"icns")
        self.assertEqual(struct.unpack(">I", icns_bytes[4:8])[0],
                         len(icns_bytes))
        entry_list = app_icon_files.read_icns_entry_list(icns_bytes)
        type_list = [type_bytes for type_bytes, _ in entry_list]
        self.assertEqual(type_list, [
            type_bytes for type_bytes, _ in
            app_icon_files.ICNS_TYPE_SIZE_TUPLE])
        for (type_bytes, data_bytes), (_, size_i) in zip(
                entry_list, app_icon_files.ICNS_TYPE_SIZE_TUPLE):
            self.assertEqual(data_bytes, png_dict[size_i])
        # The standard sizes 16 to 1024 are all there.
        self.assertEqual(
            {size_i for _, size_i in app_icon_files.ICNS_TYPE_SIZE_TUPLE},
            set(size_tuple))

    @covers("LLFR-00182")
    def test_ico_directory_points_at_each_image(self) -> None:
        """The .ico header, directory and image offsets are consistent.

        Inputs: none.
        Outputs: none.
        """
        png_dict = fake_png_dict(app_icon_files.ICO_SIZE_TUPLE)
        ico_bytes = app_icon_files.pack_ico(png_dict)
        self.assertEqual(struct.unpack("<HHH", ico_bytes[:6]),
                         (0, 1, len(app_icon_files.ICO_SIZE_TUPLE)))
        entry_list = app_icon_files.read_ico_entry_list(ico_bytes)
        self.assertEqual([side_i for side_i, _ in entry_list],
                         list(app_icon_files.ICO_SIZE_TUPLE))
        for side_i, data_bytes in entry_list:
            self.assertEqual(data_bytes, png_dict[side_i])
        # 256 is written as 0 in the directory.
        last_entry_i = 6 + 16 * (len(app_icon_files.ICO_SIZE_TUPLE) - 1)
        self.assertEqual(ico_bytes[last_entry_i], 0)

    @covers("LLFR-00182")
    def test_broken_containers_are_rejected(self) -> None:
        """The readers refuse content that is not .icns or .ico.

        Inputs: none.
        Outputs: none.
        """
        with self.assertRaises(ValueError):
            app_icon_files.read_icns_entry_list(b"abcd\x00\x00\x00\x08")
        with self.assertRaises(ValueError):
            app_icon_files.read_ico_entry_list(b"\x00\x00\x02\x00\x00\x00")

    @covers("LLFR-00182")
    def test_platform_icon_file(self) -> None:
        """macOS gets the .icns, Windows the .ico, Linux none.

        Inputs: none.
        Outputs: none.
        """
        path_dict = {"icns": "a.icns", "ico": "a.ico", "png": "a.png"}
        self.assertEqual(app_icon_files.platform_icon_path(
            path_dict, "darwin"), "a.icns")
        self.assertEqual(app_icon_files.platform_icon_path(
            path_dict, "win32"), "a.ico")
        self.assertEqual(app_icon_files.platform_icon_path(
            path_dict, "linux"), "")


@requires_qt
class AppIconFilesTest(unittest.TestCase):
    """The real icon files, drawn with Qt."""

    @covers("LLFR-00182", "LLFR-00183")
    def test_written_files_hold_the_drawn_icon(self) -> None:
        """Every image of the .icns and .ico is a PNG of its size.

        Inputs: none.
        Outputs: none.
        """
        get_qt_application()
        from PyQt6.QtGui import QImage
        with tempfile.TemporaryDirectory() as folder_str:
            path_dict = app_icon_files.write_app_icon_files(
                os.path.join(folder_str, "icons"))
            self.assertEqual(set(path_dict), {"icns", "ico", "png"})
            with open(path_dict["icns"], "rb") as icon_file:
                icns_entry_list = app_icon_files.read_icns_entry_list(
                    icon_file.read())
            with open(path_dict["ico"], "rb") as icon_file:
                ico_entry_list = app_icon_files.read_ico_entry_list(
                    icon_file.read())
            size_dict = dict(app_icon_files.ICNS_TYPE_SIZE_TUPLE)
            checked_list = [(size_dict[type_bytes], data_bytes)
                            for type_bytes, data_bytes in icns_entry_list]
            checked_list += ico_entry_list
            for side_i, data_bytes in checked_list:
                with self.subTest(size=side_i):
                    image = QImage.fromData(data_bytes, "PNG")
                    self.assertFalse(image.isNull())
                    self.assertEqual((image.width(), image.height()),
                                     (side_i, side_i))
            self.assertTrue(QImage(path_dict["png"]).width() > 0)


if __name__ == "__main__":
    unittest.main()
