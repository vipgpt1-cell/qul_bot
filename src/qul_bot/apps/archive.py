"""Defensive reading of entries from untrusted ZIP archives (APK and IPA files are ZIPs)."""

from __future__ import annotations

import copy
import zipfile
import zlib

_READ_ERRORS = (zipfile.BadZipFile, zlib.error, OSError, ValueError, EOFError, RuntimeError)


class ArchiveError(ValueError):
    """The file is not a readable archive."""


def open_archive(data: bytes) -> zipfile.ZipFile:
    import io

    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except (zipfile.BadZipFile, ValueError) as exc:
        raise ArchiveError("not a zip archive") from exc
    if len(archive.infolist()) > 200_000:
        raise ArchiveError("too many entries")
    return archive


def read_entry(archive: zipfile.ZipFile, info: zipfile.ZipInfo, limit: int) -> bytes | None:
    """The entry's bytes, or None if it is too big, corrupt or uses an unusable compression.

    The declared size is checked *before* decompressing, which defuses zip bombs: zipfile
    never inflates past the declared size (it fails the CRC/size check instead).
    An unknown compression method is handled like Android's own zip reader does: anything
    that is not "stored" is inflated; if that fails and the sizes match, it is read as stored.
    The CRC check still guards against reading garbage either way.
    """
    if info.file_size > limit:
        return None
    try:
        return archive.read(info)
    except NotImplementedError:
        pass
    except _READ_ERRORS:
        return None
    for method in (zipfile.ZIP_DEFLATED, zipfile.ZIP_STORED):
        if method == zipfile.ZIP_STORED and info.compress_size != info.file_size:
            continue
        retry = copy.copy(info)
        retry.compress_type = method
        try:
            return archive.read(retry)
        except _READ_ERRORS:
            continue
    return None


def find(archive: zipfile.ZipFile, name: str) -> zipfile.ZipInfo | None:
    try:
        return archive.getinfo(name)
    except KeyError:
        return None
