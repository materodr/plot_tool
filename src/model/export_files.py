"""Files of the Word and PNG exports, with no Qt (HLFR-00038).

- ``build_docx_bytes`` writes a Word document (Office Open XML, .docx)
  with the Python standard library only (zipfile and XML text,
  LLFR-01232, COR-00011): one landscape A4 page per tab, with the tab's
  name in bold, the description of the open data files and one PNG
  image of the tab's plots (LLFR-01231). The parts are the minimum that
  Microsoft Word and LibreOffice Writer open: ``[Content_Types].xml``,
  ``_rels/.rels``, ``word/document.xml``,
  ``word/_rels/document.xml.rels`` and ``word/media/imageN.png``, with
  ``docProps/core.xml`` and ``docProps/app.xml`` for the file
  properties.
- ``png_file_name_list`` names the PNG file of each tab (LLFR-01235).
- ``png_size_tuple`` reads the size of a PNG image from its header.
"""

import re
import struct
import zipfile
from io import BytesIO
from xml.sax.saxutils import escape

# LLFR-01230: the extension of the Word document.
DOCX_SUFFIX_STR = ".docx"
# LLFR-01235: the extension of the PNG files and the name of a tab left
# empty by the replaced characters.
PNG_SUFFIX_STR = ".png"
EMPTY_PNG_NAME_STR = "tab"
# LLFR-01235: the characters replaced in a PNG file name: all but
# letters, digits, "_", spaces and "-".
UNSAFE_NAME_CHARACTER_PATTERN_STR = r"[^\w \-]"
# LLFR-01231: the page is landscape A4 with margins of 1 cm, in
# twentieths of a point (twips), and the image fits in it.
PAGE_WIDTH_TWIPS_I = 16838
PAGE_HEIGHT_TWIPS_I = 11906
PAGE_MARGIN_TWIPS_I = 567
EMU_PER_TWIP_I = 635
# LLFR-01231: room kept on each page for the name and the description.
TEXT_ROOM_TWIPS_I = 1700
TITLE_HALF_POINTS_I = 28
DESCRIPTION_HALF_POINTS_I = 20
PNG_SIGNATURE_BYTES = b"\x89PNG\r\n\x1a\n"

CONTENT_TYPES_XML_STR = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/'
    'content-types">'
    '<Default Extension="rels" ContentType="application/'
    'vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Default Extension="png" ContentType="image/png"/>'
    '<Override PartName="/word/document.xml" ContentType="application/'
    'vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"'
    '/>'
    '<Override PartName="/docProps/core.xml" ContentType="application/'
    'vnd.openxmlformats-package.core-properties+xml"/>'
    '<Override PartName="/docProps/app.xml" ContentType="application/'
    'vnd.openxmlformats-officedocument.extended-properties+xml"/>'
    '</Types>')
PACKAGE_RELS_XML_STR = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
    'relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/'
    'officeDocument/2006/relationships/officeDocument" '
    'Target="word/document.xml"/>'
    '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/'
    'package/2006/relationships/metadata/core-properties" '
    'Target="docProps/core.xml"/>'
    '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/'
    'officeDocument/2006/relationships/extended-properties" '
    'Target="docProps/app.xml"/>'
    '</Relationships>')
CORE_XML_STR = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/'
    'package/2006/metadata/core-properties" '
    'xmlns:dc="http://purl.org/dc/elements/1.1/">'
    '<dc:title>plot_tool plots</dc:title>'
    '<dc:creator>plot_tool</dc:creator>'
    '</cp:coreProperties>')
APP_XML_STR = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/'
    '2006/extended-properties"><Application>plot_tool</Application>'
    '</Properties>')
DOCUMENT_NAMESPACES_STR = (
    'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/'
    'main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/'
    'relationships" '
    'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/'
    'wordprocessingDrawing" '
    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"')
IMAGE_RELATIONSHIP_TYPE_STR = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
    "image")


def png_size_tuple(png_bytes: bytes) -> tuple:
    """Return the width and height of a PNG image from its header.

    Inputs:
        png_bytes: the bytes of a PNG file.
    Outputs: (width, height) in pixels.
    Raises:
        ValueError: when the bytes are not a PNG image.
    """
    # LLFR-01231: the size gives the proportions of the image on the
    # page; the IHDR chunk comes first, right after the signature.
    if (len(png_bytes) < 24 or png_bytes[:8] != PNG_SIGNATURE_BYTES
            or png_bytes[12:16] != b"IHDR"):
        raise ValueError("The image is not a PNG image.")
    width_i, height_i = struct.unpack(">II", png_bytes[16:24])
    return (int(width_i), int(height_i))


def fitted_image_emu_tuple(width_px_i: int, height_px_i: int) -> tuple:
    """Return the size of an image on a page, in EMU.

    Inputs:
        width_px_i: the width of the image, in pixels.
        height_px_i: its height, in pixels.
    Outputs: (cx, cy) in English Metric Units: as large as the page's
        free width and height allow, keeping the proportions.
    """
    # LLFR-01231: the plots fill the page below the text.
    free_width_i = (PAGE_WIDTH_TWIPS_I - 2 * PAGE_MARGIN_TWIPS_I
                    ) * EMU_PER_TWIP_I
    free_height_i = (PAGE_HEIGHT_TWIPS_I - 2 * PAGE_MARGIN_TWIPS_I
                     - TEXT_ROOM_TWIPS_I) * EMU_PER_TWIP_I
    width_px_i = max(int(width_px_i), 1)
    height_px_i = max(int(height_px_i), 1)
    scale_f = min(free_width_i / width_px_i, free_height_i / height_px_i)
    return (max(int(width_px_i * scale_f), 1),
            max(int(height_px_i * scale_f), 1))


def text_paragraph_xml(text_str: str, half_points_i: int,
                       bold_b: bool) -> str:
    """Return the XML of a paragraph of one run of text.

    Inputs:
        text_str: the text.
        half_points_i: the font size, in half points.
        bold_b: True for bold letters.
    Outputs: a ``w:p`` element as text.
    """
    # LLFR-01231: the tab's name and the description of the files.
    bold_str = "<w:b/>" if bold_b else ""
    return (f'<w:p><w:r><w:rPr>{bold_str}<w:sz w:val="{half_points_i}"/>'
            f'</w:rPr><w:t xml:space="preserve">{escape(text_str)}</w:t>'
            f'</w:r></w:p>')


def image_paragraph_xml(relationship_id_str: str, picture_number_i: int,
                        size_emu_tuple: tuple) -> str:
    """Return the XML of a paragraph that holds one inline picture.

    Inputs:
        relationship_id_str: the id of the image relationship.
        picture_number_i: a number unique in the document, from 1.
        size_emu_tuple: (cx, cy) of the picture, in EMU.
    Outputs: a ``w:p`` element with a ``wp:inline`` drawing.
    """
    # LLFR-01231, LLFR-01232: an inline DrawingML picture, as Word and
    # LibreOffice write them.
    cx_i, cy_i = (int(value_i) for value_i in size_emu_tuple)
    name_str = f"Plots {picture_number_i}"
    return (
        '<w:p><w:r><w:drawing>'
        '<wp:inline distT="0" distB="0" distL="0" distR="0">'
        f'<wp:extent cx="{cx_i}" cy="{cy_i}"/>'
        '<wp:effectExtent l="0" t="0" r="0" b="0"/>'
        f'<wp:docPr id="{picture_number_i}" name="{name_str}"/>'
        '<wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/>'
        '</wp:cNvGraphicFramePr>'
        '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/'
        'drawingml/2006/picture"><pic:pic>'
        f'<pic:nvPicPr><pic:cNvPr id="{picture_number_i}" '
        f'name="{name_str}"/><pic:cNvPicPr/></pic:nvPicPr>'
        f'<pic:blipFill><a:blip r:embed="{relationship_id_str}"/>'
        '<a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
        '<pic:spPr><a:xfrm><a:off x="0" y="0"/>'
        f'<a:ext cx="{cx_i}" cy="{cy_i}"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
        '</pic:pic></a:graphicData></a:graphic></wp:inline>'
        '</w:drawing></w:r></w:p>')


def document_xml(page_list: list) -> str:
    """Return the text of ``word/document.xml``.

    Inputs:
        page_list: one (tab name, description, PNG bytes) per page.
    Outputs: the XML text: per page, the name in bold, the description
        when there is one and the image, with a page break before every
        page but the first, and a landscape A4 section.
    """
    # LLFR-01231: one page per tab, in tab order.
    body_list = []
    for page_index_i, (name_str, description_str,
                       png_bytes) in enumerate(page_list):
        if page_index_i > 0:
            body_list.append('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')
        body_list.append(text_paragraph_xml(str(name_str),
                                            TITLE_HALF_POINTS_I, True))
        if description_str:
            body_list.append(text_paragraph_xml(
                str(description_str), DESCRIPTION_HALF_POINTS_I, False))
        size_tuple = fitted_image_emu_tuple(*png_size_tuple(png_bytes))
        body_list.append(image_paragraph_xml(f"rIdImage{page_index_i + 1}",
                                             page_index_i + 1, size_tuple))
    margin_i = PAGE_MARGIN_TWIPS_I
    section_str = (
        f'<w:sectPr><w:pgSz w:w="{PAGE_WIDTH_TWIPS_I}" '
        f'w:h="{PAGE_HEIGHT_TWIPS_I}" w:orient="landscape"/>'
        f'<w:pgMar w:top="{margin_i}" w:right="{margin_i}" '
        f'w:bottom="{margin_i}" w:left="{margin_i}" w:header="0" '
        'w:footer="0" w:gutter="0"/></w:sectPr>')
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            f'<w:document {DOCUMENT_NAMESPACES_STR}><w:body>'
            + "".join(body_list) + section_str + '</w:body></w:document>')


def document_rels_xml(page_count_i: int) -> str:
    """Return the text of ``word/_rels/document.xml.rels``.

    Inputs:
        page_count_i: the number of pages, one image each.
    Outputs: the XML text with one image relationship per page.
    """
    # LLFR-01232: each picture points at its PNG part.
    relationship_list = [
        f'<Relationship Id="rIdImage{number_i}" '
        f'Type="{IMAGE_RELATIONSHIP_TYPE_STR}" '
        f'Target="media/image{number_i}.png"/>'
        for number_i in range(1, int(page_count_i) + 1)]
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/'
            'package/2006/relationships">' + "".join(relationship_list)
            + '</Relationships>')


def build_docx_bytes(page_list: list) -> bytes:
    """Return the bytes of a Word document with one page per tab.

    Inputs:
        page_list: one (tab name, description of the data files, PNG
            bytes of the tab's plots) per page, in tab order.
    Outputs: the bytes of the .docx file (a ZIP archive).
    Raises:
        ValueError: when an image is not a PNG image.
    """
    # LLFR-01232: built with zipfile and XML text only (COR-00011); the
    # content types come first, as Word expects.
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", CONTENT_TYPES_XML_STR)
        archive.writestr("_rels/.rels", PACKAGE_RELS_XML_STR)
        archive.writestr("docProps/core.xml", CORE_XML_STR)
        archive.writestr("docProps/app.xml", APP_XML_STR)
        archive.writestr("word/document.xml", document_xml(page_list))
        archive.writestr("word/_rels/document.xml.rels",
                         document_rels_xml(len(page_list)))
        for page_index_i, page_tuple in enumerate(page_list):
            # LLFR-01231: the PNG image of the page's plots, stored as it
            # is (already compressed).
            archive.writestr(
                zipfile.ZipInfo(f"word/media/image{page_index_i + 1}.png"),
                bytes(page_tuple[2]))
    return buffer.getvalue()


def ensure_docx_suffix(path_str: str) -> str:
    """Return the path with ``.docx`` added when it has another ending.

    Inputs:
        path_str: the path chosen in the save file dialog.
    Outputs: path_str when it ends with ``.docx`` (in any case), else
        path_str followed by ``.docx``.
    """
    # LLFR-01230: the saved file is always a .docx file.
    if str(path_str).lower().endswith(DOCX_SUFFIX_STR):
        return str(path_str)
    return str(path_str) + DOCX_SUFFIX_STR


def png_file_name_list(tab_name_list: list) -> list:
    """Return the PNG file name of each tab of an export.

    Inputs:
        tab_name_list: the names of the exported tabs, in tab order.
    Outputs: one file name per tab: the name with every character
        other than a letter, a digit, a space or ``-`` replaced by
        ``_`` (``_`` itself is kept), ``tab`` for an empty result, then
        ``_2``, ``_3`` and so on for a name already given in the export,
        compared ignoring case, and ``.png``.
    """
    # LLFR-01235: names safe on macOS and on Windows, unique in the
    # folder even on a file system that ignores case.
    used_set = set()
    file_name_list = []
    for tab_name_str in tab_name_list:
        base_str = re.sub(UNSAFE_NAME_CHARACTER_PATTERN_STR, "_",
                          str(tab_name_str)).strip()
        if not base_str.strip("_ "):
            base_str = EMPTY_PNG_NAME_STR
        candidate_str = base_str
        number_i = 2
        while candidate_str.casefold() in used_set:
            candidate_str = f"{base_str}_{number_i}"
            number_i += 1
        used_set.add(candidate_str.casefold())
        file_name_list.append(candidate_str + PNG_SUFFIX_STR)
    return file_name_list
