"""Tests for the files of the Word and PNG exports (no Qt needed).

They check the Word document built with the standard library only
(LLFR-01231, LLFR-01232) and the names of the PNG files (LLFR-01235).
"""

import struct
import unittest
import zipfile
import zlib
from io import BytesIO
from xml.etree import ElementTree

from tests.support import covers

from model.export_files import (
    build_docx_bytes, ensure_docx_suffix, fitted_image_emu_tuple,
    png_file_name_list, png_size_tuple)

WORD_NAMESPACE_STR = (
    "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}")
RELATIONSHIP_NAMESPACE_STR = (
    "{http://schemas.openxmlformats.org/package/2006/relationships}")
EXTENT_TAG_STR = ("{http://schemas.openxmlformats.org/drawingml/2006/"
                  "wordprocessingDrawing}extent")
BLIP_TAG_STR = "{http://schemas.openxmlformats.org/drawingml/2006/main}blip"
EMBED_ATTRIBUTE_STR = ("{http://schemas.openxmlformats.org/officeDocument/"
                       "2006/relationships}embed")


def tiny_png_bytes(width_i: int, height_i: int) -> bytes:
    """Return a valid grey PNG image, written with zlib and struct.

    Inputs:
        width_i: its width in pixels.
        height_i: its height in pixels.
    Outputs: the bytes of the PNG file.
    """
    def chunk(kind_bytes: bytes, data_bytes: bytes) -> bytes:
        """Return one PNG chunk.

        Inputs:
            kind_bytes: the 4-byte chunk type.
            data_bytes: the chunk data.
        Outputs: the chunk with its length and CRC.
        """
        return (struct.pack(">I", len(data_bytes)) + kind_bytes + data_bytes
                + struct.pack(">I", zlib.crc32(kind_bytes + data_bytes)))

    row_bytes = b"\x00" + b"\x80" * width_i
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width_i, height_i, 8,
                                         0, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(row_bytes * height_i))
            + chunk(b"IEND", b""))


class DocxTest(unittest.TestCase):
    """The Word document of "Save all tabs as Word document"."""

    def setUp(self) -> None:
        """Build a document of two pages.

        Inputs: none.
        Outputs: none.
        """
        self.page_list = [("Tab 1", "file1 = a.csv", tiny_png_bytes(40, 20)),
                          ("A & <B>", "", tiny_png_bytes(10, 30))]
        self.archive = zipfile.ZipFile(BytesIO(build_docx_bytes(
            self.page_list)))

    def tearDown(self) -> None:
        """Close the archive.

        Inputs: none.
        Outputs: none.
        """
        self.archive.close()

    @covers("LLFR-01232", "HLFR-00038")
    def test_parts_of_a_minimal_docx(self) -> None:
        """The archive holds the parts Word and LibreOffice need, every
        XML part parses, and the content types come first.

        Inputs: none.
        Outputs: none.
        """
        name_list = self.archive.namelist()
        self.assertEqual(name_list[0], "[Content_Types].xml")
        for part_str in ("_rels/.rels", "word/document.xml",
                         "word/_rels/document.xml.rels",
                         "word/media/image1.png", "word/media/image2.png",
                         "docProps/core.xml", "docProps/app.xml"):
            self.assertIn(part_str, name_list)
        for part_str in name_list:
            if part_str.endswith((".xml", ".rels")):
                ElementTree.fromstring(self.archive.read(part_str))
        self.assertIsNone(self.archive.testzip())
        content_str = self.archive.read("[Content_Types].xml").decode()
        self.assertIn('Extension="png"', content_str)
        self.assertIn("wordprocessingml.document.main+xml", content_str)

    @covers("LLFR-01231", "LLFR-01232", "HLFR-00038")
    def test_one_page_per_tab_with_name_text_and_image(self) -> None:
        """Each page has the bold name, the description when there is
        one and a picture whose relationship leads to its PNG, with page
        breaks between the pages and a landscape A4 section.

        Inputs: none.
        Outputs: none.
        """
        root = ElementTree.fromstring(self.archive.read("word/document.xml"))
        text_list = [node.text for node in root.iter(WORD_NAMESPACE_STR + "t")]
        self.assertEqual(text_list, ["Tab 1", "file1 = a.csv", "A & <B>"])
        self.assertEqual(len(list(root.iter(WORD_NAMESPACE_STR + "b"))), 2)
        break_list = [node for node in root.iter(WORD_NAMESPACE_STR + "br")
                      if node.get(WORD_NAMESPACE_STR + "type") == "page"]
        self.assertEqual(len(break_list), 1)
        size_node = next(root.iter(WORD_NAMESPACE_STR + "pgSz"))
        self.assertEqual(size_node.get(WORD_NAMESPACE_STR + "orient"),
                         "landscape")
        rels_root = ElementTree.fromstring(
            self.archive.read("word/_rels/document.xml.rels"))
        target_dict = {node.get("Id"): node.get("Target")
                       for node in rels_root.iter(
                           RELATIONSHIP_NAMESPACE_STR + "Relationship")}
        embed_list = [node.get(EMBED_ATTRIBUTE_STR)
                      for node in root.iter(BLIP_TAG_STR)]
        self.assertEqual(len(embed_list), 2)
        for index_i, embed_str in enumerate(embed_list):
            target_str = "word/" + target_dict[embed_str]
            self.assertEqual(self.archive.read(target_str),
                             self.page_list[index_i][2])
        # The pictures keep the proportions of their images.
        extent_list = [(int(node.get("cx")), int(node.get("cy")))
                       for node in root.iter(EXTENT_TAG_STR)]
        self.assertAlmostEqual(extent_list[0][0] / extent_list[0][1], 2.0,
                               places=3)
        self.assertAlmostEqual(extent_list[1][1] / extent_list[1][0], 3.0,
                               places=3)

    @covers("LLFR-01231")
    def test_image_fits_the_page(self) -> None:
        """A wide and a tall image both stay inside the free area.

        Inputs: none.
        Outputs: none.
        """
        wide_tuple = fitted_image_emu_tuple(4000, 100)
        tall_tuple = fitted_image_emu_tuple(100, 4000)
        self.assertLessEqual(wide_tuple[0], (16838 - 2 * 567) * 635)
        self.assertLessEqual(tall_tuple[1], (11906 - 2 * 567 - 1700) * 635)
        self.assertEqual(png_size_tuple(tiny_png_bytes(7, 5)), (7, 5))
        with self.assertRaises(ValueError):
            png_size_tuple(b"not a png at all, sorry")
        with self.assertRaises(ValueError):
            build_docx_bytes([("Tab", "", b"no png")])

    @covers("LLFR-01230")
    def test_docx_suffix(self) -> None:
        """".docx" is added only when the path has another ending.

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(ensure_docx_suffix("/a/b"), "/a/b.docx")
        self.assertEqual(ensure_docx_suffix("/a/b.DOCX"), "/a/b.DOCX")


class PngNameTest(unittest.TestCase):
    """The names of the PNG files of "Save each tab as PNG"."""

    @covers("LLFR-01235", "HLFR-00038")
    def test_names_safe_and_unique_ignoring_case(self) -> None:
        """Unsafe characters become "_", an empty name becomes "tab",
        and names already given get "_2", "_3".

        Inputs: none.
        Outputs: none.
        """
        self.assertEqual(
            png_file_name_list(["Tab 1", "a/b", "A?b", "", "Engine-1",
                                "a_b", "x.y"]),
            ["Tab 1.png", "a_b.png", "A_b_2.png", "tab.png",
             "Engine-1.png", "a_b_3.png", "x_y.png"])
        self.assertEqual(png_file_name_list(["Tab", "tab", "TAB"]),
                         ["Tab.png", "tab_2.png", "TAB_3.png"])


if __name__ == "__main__":
    unittest.main()
