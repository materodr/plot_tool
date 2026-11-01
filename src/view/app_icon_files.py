"""Icon files of the standalone executable (LLFR-00182).

build_executable.py calls ``write_app_icon_files`` before it runs
PyInstaller, and passes the file that suits the platform to PyInstaller's
``--icon`` option: an ``.icns`` file on macOS (it becomes the app
bundle's icon, shown in Finder, the Dock and the app switcher) and an
``.ico`` file on Windows (the icon of the ``.exe`` and of the taskbar
button). The files are drawn from the same vector drawing as the window
icon (view.icons, LLFR-00183) at the standard sizes, and packed here in
Python, so no extra library or macOS tool is needed (COR-00011). They
are build outputs, written to the build folder and never committed
(COR-00007).

Both containers hold PNG images:
- ICNS: the bytes ``icns`` and the total length, then for each image a
  4-byte type (which says its size), the entry length and the PNG data;
  all numbers are big-endian.
- ICO: a 6-byte header (0, type 1, image count), one 16-byte directory
  entry per image (width and height, 0 meaning 256, then planes, bits
  per pixel, data length and data offset, little-endian) and the PNG
  data of each image.

The packing functions do not import Qt; only ``write_app_icon_files``
draws the images, through view.icons.
"""

import os
import struct

APP_ICON_BASE_NAME_STR = "plot_tool"
# LLFR-00182: ICNS entry type -> side of its PNG image in pixels. The
# @2x types (ic10 to ic14) hold the high density version of a size.
ICNS_TYPE_SIZE_TUPLE = (
    (b"icp4", 16), (b"icp5", 32), (b"ic07", 128),
    (b"ic08", 256), (b"ic09", 512), (b"ic10", 1024), (b"ic11", 32),
    (b"ic12", 64), (b"ic13", 256), (b"ic14", 512),
)
# LLFR-00182: the sizes of a Windows icon (256 is the largest ICO size).
ICO_SIZE_TUPLE = (16, 24, 32, 48, 64, 128, 256)
# LLFR-00182: macOS app icons leave an empty border around the rounded
# square (about 100 px of 1024 in Apple's icon grid), so the icon has
# the same visual size as the other apps in the Dock.
MACOS_MARGIN_FRACTION_F = 0.098
ICNS_HEADER_SIZE_I = 8
ICO_HEADER_SIZE_I = 6
ICO_ENTRY_SIZE_I = 16


def pack_icns(png_bytes_dict: dict) -> bytes:
    """Pack PNG images into the content of a macOS .icns file.

    Inputs:
        png_bytes_dict: side in pixels -> PNG bytes; must hold every
            size of ICNS_TYPE_SIZE_TUPLE.
    Outputs: the .icns file content.
    """
    # LLFR-00182: one entry per ICNS type, in the order of the tuple.
    entry_bytes_list = []
    for type_bytes, size_i in ICNS_TYPE_SIZE_TUPLE:
        png_bytes = png_bytes_dict[size_i]
        entry_bytes_list.append(type_bytes + struct.pack(
            ">I", ICNS_HEADER_SIZE_I + len(png_bytes)) + png_bytes)
    body_bytes = b"".join(entry_bytes_list)
    return (b"icns" + struct.pack(">I", ICNS_HEADER_SIZE_I + len(body_bytes))
            + body_bytes)


def pack_ico(png_bytes_dict: dict) -> bytes:
    """Pack PNG images into the content of a Windows .ico file.

    Inputs:
        png_bytes_dict: side in pixels -> PNG bytes; must hold every
            size of ICO_SIZE_TUPLE.
    Outputs: the .ico file content.
    """
    # LLFR-00182: the header, the directory, then the images.
    image_count_i = len(ICO_SIZE_TUPLE)
    header_bytes = struct.pack("<HHH", 0, 1, image_count_i)
    offset_i = ICO_HEADER_SIZE_I + ICO_ENTRY_SIZE_I * image_count_i
    entry_bytes_list = []
    image_bytes_list = []
    for size_i in ICO_SIZE_TUPLE:
        png_bytes = png_bytes_dict[size_i]
        # A side of 256 is written as 0, the format's largest size.
        side_byte_i = size_i if size_i < 256 else 0
        entry_bytes_list.append(struct.pack(
            "<BBBBHHII", side_byte_i, side_byte_i, 0, 0, 1, 32,
            len(png_bytes), offset_i))
        image_bytes_list.append(png_bytes)
        offset_i += len(png_bytes)
    return header_bytes + b"".join(entry_bytes_list + image_bytes_list)


def read_icns_entry_list(icns_bytes: bytes) -> list:
    """Read back the entries of .icns content (used by the tests).

    Inputs:
        icns_bytes: the content of an .icns file.
    Outputs: a list of (type_bytes, data_bytes) tuples. Raises
        ValueError when the content is not a valid .icns file.
    """
    # LLFR-00182: the inverse of pack_icns.
    if icns_bytes[:4] != b"icns" or struct.unpack(
            ">I", icns_bytes[4:8])[0] != len(icns_bytes):
        raise ValueError("not an icns file")
    entry_list = []
    position_i = ICNS_HEADER_SIZE_I
    while position_i < len(icns_bytes):
        type_bytes = icns_bytes[position_i:position_i + 4]
        length_i = struct.unpack(
            ">I", icns_bytes[position_i + 4:position_i + 8])[0]
        if length_i < ICNS_HEADER_SIZE_I:
            raise ValueError("bad icns entry length")
        entry_list.append((type_bytes, icns_bytes[
            position_i + ICNS_HEADER_SIZE_I:position_i + length_i]))
        position_i += length_i
    if position_i != len(icns_bytes):
        raise ValueError("icns entries overrun the file")
    return entry_list


def read_ico_entry_list(ico_bytes: bytes) -> list:
    """Read back the images of .ico content (used by the tests).

    Inputs:
        ico_bytes: the content of an .ico file.
    Outputs: a list of (side_i, data_bytes) tuples. Raises ValueError
        when the content is not a valid .ico file.
    """
    # LLFR-00182: the inverse of pack_ico.
    reserved_i, type_i, count_i = struct.unpack("<HHH", ico_bytes[:6])
    if reserved_i != 0 or type_i != 1:
        raise ValueError("not an ico file")
    entry_list = []
    for index_i in range(count_i):
        start_i = ICO_HEADER_SIZE_I + ICO_ENTRY_SIZE_I * index_i
        (width_i, _, _, _, _, _, length_i, offset_i) = struct.unpack(
            "<BBBBHHII", ico_bytes[start_i:start_i + ICO_ENTRY_SIZE_I])
        if offset_i + length_i > len(ico_bytes):
            raise ValueError("ico image overruns the file")
        entry_list.append((width_i or 256,
                           ico_bytes[offset_i:offset_i + length_i]))
    return entry_list


def write_app_icon_files(folder_str: str) -> dict:
    """Draw the app icon and write its .icns, .ico and .png files.

    Inputs:
        folder_str: the folder to write to; it is created if needed.
    Outputs: a dict with the keys "icns", "ico" and "png" and the paths
        of the written files as values.
    """
    # LLFR-00182, LLFR-00183: the executable icon is the window icon's
    # drawing; Qt is imported only here, so the packing functions can be
    # used without it.
    from view import icons
    os.makedirs(folder_str, exist_ok=True)
    macos_png_dict = {
        size_i: icons.app_icon_png_bytes(size_i, MACOS_MARGIN_FRACTION_F)
        for size_i in sorted({entry_tuple[1]
                              for entry_tuple in ICNS_TYPE_SIZE_TUPLE})}
    windows_png_dict = {size_i: icons.app_icon_png_bytes(size_i)
                        for size_i in ICO_SIZE_TUPLE}
    content_dict = {
        "icns": pack_icns(macos_png_dict),
        "ico": pack_ico(windows_png_dict),
        "png": icons.app_icon_png_bytes(512),
    }
    path_dict = {}
    for extension_str, content_bytes in content_dict.items():
        path_str = os.path.join(
            folder_str, f"{APP_ICON_BASE_NAME_STR}.{extension_str}")
        with open(path_str, "wb") as icon_file:
            icon_file.write(content_bytes)
        path_dict[extension_str] = path_str
    return path_dict


def platform_icon_path(path_dict: dict, platform_str: str) -> str:
    """Return the icon file PyInstaller needs on a platform.

    Inputs:
        path_dict: the dict returned by write_app_icon_files.
        platform_str: a value of sys.platform.
    Outputs: the .icns path on macOS, the .ico path on Windows, and ""
        elsewhere (Linux executables carry no icon).
    """
    # LLFR-00182: PyInstaller takes an .icns on macOS, an .ico on
    # Windows.
    if platform_str == "darwin":
        return path_dict["icns"]
    if platform_str == "win32":
        return path_dict["ico"]
    return ""
