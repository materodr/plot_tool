"""Safe writing of an exported file (LLFR-00131).

The bytes are written to a temporary file in the target's folder, which
is checked and then moved onto the target in one step (``os.replace``).
So a failed export never deletes or damages a file that was there
before: only the temporary file this module created is removed. A
target that exists but may not be written (read-only) is refused before
anything is written, because ``os.replace`` would otherwise replace it.

This module holds no Qt code, so it can be tested without PyQt6.
"""

import errno
import os
import stat
import tempfile

# LLFR-00131: reasons given when the file could not be written.
EMPTY_CONTENT_REASON_STR = "There was nothing to write to the file."
INCOMPLETE_WRITE_REASON_STR = "The file was not completely written."
TEMPORARY_SUFFIX_STR = ".tmp"
# LLFR-00131: permissions of a new file before the user's umask.
NEW_FILE_MODE_I = 0o666


def describe_error(error, path_str: str) -> str:
    """Return a readable reason for an error while writing a file.

    Inputs:
        error: the OSError raised while writing.
        path_str: the path of the target file, named in the reason.
    Outputs: the error's text followed by the target path.
    """
    # LLFR-00131: the error box says why the file was not saved; it
    # names the file the user chose, not the temporary file.
    reason_str = error.strerror or str(error)
    return f"{reason_str}: {path_str}"


def current_umask_i() -> int:
    """Return the file creation mask of the process.

    Inputs: none.
    Outputs: the umask as an int.
    """
    # LLFR-00131: a new export gets the usual permissions of new files.
    umask_i = os.umask(0)
    os.umask(umask_i)
    return umask_i


def write_content(output_file, content_bytes: bytes) -> None:
    """Write all bytes to an open file and push them to the disk.

    Inputs:
        output_file: a file object opened for binary writing.
        content_bytes: the bytes to write.
    Outputs: none. Raises OSError when the write fails.
    """
    # LLFR-00131: a full disk raises here and is reported.
    output_file.write(content_bytes)
    output_file.flush()
    os.fsync(output_file.fileno())


def remove_temporary_file(temporary_path_str: str) -> None:
    """Remove the temporary file of a failed write, if it is still there.

    Inputs:
        temporary_path_str: the path of the temporary file.
    Outputs: none. Errors while removing are ignored.
    """
    # LLFR-00131: only the file this module created is removed.
    try:
        if os.path.isfile(temporary_path_str):
            os.remove(temporary_path_str)
    except OSError:
        pass


def refusal_reason(path_str: str) -> str:
    """Return why a target path cannot be written, before writing.

    Inputs:
        path_str: the path of the target file.
    Outputs: the reason, or "" when the path may be written.
    """
    # LLFR-00131: a folder or a read-only file is never replaced.
    if os.path.isdir(path_str):
        return f"{os.strerror(errno.EISDIR)}: {path_str}"
    if os.path.exists(path_str) and not os.access(path_str, os.W_OK):
        return f"{os.strerror(errno.EACCES)}: {path_str}"
    return ""


def write_file_safely(path_str: str, content_bytes: bytes) -> tuple:
    """Write bytes to a file without risking the file already there.

    Inputs:
        path_str: the path of the target file.
        content_bytes: the bytes to write.
    Outputs: a tuple (written_b, reason_str); reason_str is "" when the
        file was written and otherwise says why it was not. On failure
        the target is left exactly as it was.
    """
    # LLFR-00131: check what can be checked before writing anything.
    if not content_bytes:
        return (False, EMPTY_CONTENT_REASON_STR)
    reason_str = refusal_reason(path_str)
    if reason_str:
        return (False, reason_str)
    folder_str = os.path.dirname(os.path.abspath(path_str))
    base_name_str = os.path.basename(path_str)
    try:
        descriptor_i, temporary_path_str = tempfile.mkstemp(
            prefix=f".{base_name_str}.", suffix=TEMPORARY_SUFFIX_STR,
            dir=folder_str)
    except OSError as error:
        # LLFR-00131: missing folder or no permission in the folder.
        return (False, describe_error(error, path_str))
    try:
        with os.fdopen(descriptor_i, "wb") as output_file:
            write_content(output_file, content_bytes)
        # LLFR-00131: an incomplete write is a failed write.
        if os.path.getsize(temporary_path_str) != len(content_bytes):
            raise OSError(errno.EIO, INCOMPLETE_WRITE_REASON_STR)
        # LLFR-00131: keep the permissions of a replaced file; a new one
        # gets the usual permissions instead of the private ones of
        # mkstemp.
        if os.path.exists(path_str):
            os.chmod(temporary_path_str,
                     stat.S_IMODE(os.stat(path_str).st_mode))
        else:
            os.chmod(temporary_path_str,
                     NEW_FILE_MODE_I & ~current_umask_i())
        os.replace(temporary_path_str, path_str)
    except OSError as error:
        remove_temporary_file(temporary_path_str)
        return (False, describe_error(error, path_str))
    return (True, "")
