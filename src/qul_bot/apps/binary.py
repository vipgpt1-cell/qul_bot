"""Android's binary resource formats: compiled XML (AndroidManifest.xml) and resources.arsc."""

from __future__ import annotations

import struct
from dataclasses import dataclass, field

STRING_POOL = 0x0001
TABLE = 0x0002
XML = 0x0003
XML_START_ELEMENT = 0x0102
XML_END_ELEMENT = 0x0103
XML_RESOURCE_MAP = 0x0180
TABLE_PACKAGE = 0x0200
TABLE_TYPE = 0x0201

TYPE_REFERENCE = 0x01
TYPE_STRING = 0x03
TYPE_INT_DEC = 0x10
TYPE_INT_HEX = 0x11
TYPE_BOOLEAN = 0x12
NO_INDEX = 0xFFFFFFFF

#: Well-known framework attribute ids. Release builds often strip or obfuscate attribute
#: *names*; the resource map keeps the ids, so these are the reliable way to read them.
ATTRIBUTE_IDS = {
    0x01010001: "label",
    0x01010003: "name",
    0x0101000F: "debuggable",
    0x01010010: "exported",
    0x0101020C: "minSdkVersion",
    0x0101021B: "versionCode",
    0x0101021C: "versionName",
    0x01010270: "targetSdkVersion",
    0x01010271: "maxSdkVersion",
    0x01010280: "allowBackup",
    0x010104EC: "usesCleartextTraffic",
}


class BinaryFormatError(ValueError):
    """The bytes are not the expected Android binary format."""


@dataclass(frozen=True, slots=True)
class Reference:
    """`@0x7f060000`: points into resources.arsc."""

    resource_id: int


AttrValue = str | int | bool | Reference


@dataclass(slots=True)
class Element:
    name: str
    attrs: dict[str, AttrValue] = field(default_factory=dict)
    children: list[Element] = field(default_factory=list)

    def iter(self, name: str) -> list[Element]:
        """All descendants (and self) with this tag name, in document order."""
        found = [self] if self.name == name else []
        for child in self.children:
            found += child.iter(name)
        return found

    def find(self, name: str) -> Element | None:
        matches = self.iter(name)
        return matches[0] if matches else None


def _unpack(fmt: str, data: bytes, offset: int) -> tuple[int, ...]:
    try:
        return struct.unpack_from(fmt, data, offset)
    except struct.error as exc:
        raise BinaryFormatError(f"truncated data at {offset}") from exc


def _length8(data: bytes, pos: int) -> tuple[int, int]:
    first = data[pos]
    if first & 0x80:
        return ((first & 0x7F) << 8) | data[pos + 1], pos + 2
    return first, pos + 1


def _length16(data: bytes, pos: int) -> tuple[int, int]:
    (first,) = _unpack("<H", data, pos)
    if first & 0x8000:
        (second,) = _unpack("<H", data, pos + 2)
        return ((first & 0x7FFF) << 16) | second, pos + 4
    return first, pos + 2


def parse_string_pool(data: bytes, offset: int) -> list[str]:
    _, header_size, _ = _unpack("<HHI", data, offset)
    count, _, flags, strings_start, _ = _unpack("<IIIII", data, offset + 8)
    if count > 2_000_000:
        raise BinaryFormatError("string pool too large")
    utf8 = bool(flags & 0x100)
    offsets = _unpack(f"<{count}I", data, offset + header_size) if count else ()
    base = offset + strings_start
    strings: list[str] = []
    try:
        for string_offset in offsets:
            pos = base + string_offset
            if utf8:
                _, pos = _length8(data, pos)  # length in UTF-16 units, unused
                size, pos = _length8(data, pos)
                strings.append(data[pos : pos + size].decode("utf-8", errors="replace"))
            else:
                size, pos = _length16(data, pos)
                strings.append(data[pos : pos + 2 * size].decode("utf-16-le", errors="replace"))
    except IndexError as exc:
        raise BinaryFormatError("string pool out of bounds") from exc
    return strings


def _string(strings: list[str], index: int) -> str:
    return strings[index] if 0 <= index < len(strings) else ""


def _signed32(value: int) -> int:
    return value - (1 << 32) if value & 0x80000000 else value


def _typed_value(dtype: int, data: int, raw: int, strings: list[str]) -> AttrValue:
    if dtype == TYPE_STRING:
        return _string(strings, data)
    if dtype in (TYPE_INT_DEC, TYPE_INT_HEX):
        return _signed32(data)
    if dtype == TYPE_BOOLEAN:
        return data != 0
    if dtype == TYPE_REFERENCE:
        return Reference(data)
    if raw != NO_INDEX:
        return _string(strings, raw)
    return data


def parse_xml(data: bytes) -> Element:
    """Decode a compiled (binary) Android XML document into a tree."""
    kind, header_size, size = _unpack("<HHI", data, 0)
    if kind != XML:
        raise BinaryFormatError("not a binary XML document")
    end = min(size, len(data))
    pos = header_size
    strings: list[str] = []
    resource_ids: tuple[int, ...] = ()
    root: Element | None = None
    stack: list[Element] = []

    while pos + 8 <= end:
        chunk_type, chunk_header, chunk_size = _unpack("<HHI", data, pos)
        if chunk_size < 8:
            raise BinaryFormatError("corrupt chunk size")
        if chunk_type == STRING_POOL:
            strings = parse_string_pool(data, pos)
        elif chunk_type == XML_RESOURCE_MAP:
            count = (chunk_size - chunk_header) // 4
            resource_ids = _unpack(f"<{count}I", data, pos + chunk_header)
        elif chunk_type == XML_START_ELEMENT:
            ext = pos + chunk_header
            _, name_index, attr_start, attr_size, attr_count = _unpack("<IIHHH", data, ext)
            element = Element(_string(strings, name_index))
            for i in range(attr_count):
                at = ext + attr_start + i * attr_size
                _, attr_name, raw, _, _, dtype, value = _unpack("<IIIHBBI", data, at)
                name = ATTRIBUTE_IDS.get(
                    resource_ids[attr_name] if attr_name < len(resource_ids) else -1
                ) or _string(strings, attr_name)
                element.attrs[name] = _typed_value(dtype, value, raw, strings)
            if stack:
                stack[-1].children.append(element)
            elif root is None:
                root = element
            stack.append(element)
        elif chunk_type == XML_END_ELEMENT and stack:
            stack.pop()
        pos += chunk_size

    if root is None:
        raise BinaryFormatError("no root element")
    return root


def resolve_string(table: bytes, resource_id: int, _depth: int = 0) -> str | None:
    """Look up a string resource (e.g. the app label) in resources.arsc.

    Prefers the default configuration; falls back to the first one that has a value.
    Returns None when the id is missing or not a string.
    """
    if _depth > 4:
        return None
    kind, header_size, _ = _unpack("<HHI", table, 0)
    if kind != TABLE:
        raise BinaryFormatError("not a resource table")
    package_id, type_id, entry = resource_id >> 24, (resource_id >> 16) & 0xFF, resource_id & 0xFFFF
    global_strings: list[str] | None = None
    fallback: tuple[int, int] | None = None
    pos = header_size
    while pos + 8 <= len(table):
        chunk_type, chunk_header, chunk_size = _unpack("<HHI", table, pos)
        if chunk_size < 8:
            raise BinaryFormatError("corrupt chunk size")
        if chunk_type == STRING_POOL and global_strings is None:
            global_strings = parse_string_pool(table, pos)
        elif chunk_type == TABLE_PACKAGE and _unpack("<I", table, pos + 8)[0] == package_id:
            inner, end = pos + chunk_header, pos + chunk_size
            while inner + 8 <= end:
                inner_type, inner_header, inner_size = _unpack("<HHI", table, inner)
                if inner_size < 8:
                    raise BinaryFormatError("corrupt chunk size")
                if inner_type == TABLE_TYPE:
                    found = _entry_value(table, inner, inner_header, type_id, entry)
                    if found is not None:
                        is_default, value = found
                        if is_default:
                            return _as_string(table, value, global_strings, _depth)
                        fallback = fallback or value
                inner += inner_size
        pos += chunk_size
    return _as_string(table, fallback, global_strings, _depth) if fallback else None


def _as_string(
    table: bytes, value: tuple[int, int] | None, strings: list[str] | None, depth: int
) -> str | None:
    if value is None:
        return None
    dtype, data = value
    if dtype == TYPE_STRING and strings is not None:
        return _string(strings, data)
    if dtype == TYPE_REFERENCE:
        return resolve_string(table, data, depth + 1)
    return None


def _entry_value(
    table: bytes, chunk: int, header_size: int, type_id: int, entry: int
) -> tuple[bool, tuple[int, int]] | None:
    """(is default config, (data type, data)) of `entry` in a type chunk, if present."""
    chunk_type_id, flags = table[chunk + 8], table[chunk + 9]
    if chunk_type_id != type_id:
        return None
    entry_count, entries_start = _unpack("<II", table, chunk + 12)
    (config_size,) = _unpack("<I", table, chunk + 20)
    is_default = not any(table[chunk + 24 : chunk + 20 + config_size])
    offsets = chunk + header_size

    if flags & 0x01:  # sparse: (index, offset/4) pairs
        offset = None
        for i in range(entry_count):
            index, half = _unpack("<HH", table, offsets + 4 * i)
            if index == entry:
                offset = half * 4
                break
        if offset is None:
            return None
    elif flags & 0x02:  # 16-bit offsets
        if entry >= entry_count:
            return None
        (half,) = _unpack("<H", table, offsets + 2 * entry)
        if half == 0xFFFF:
            return None
        offset = half * 4
    else:
        if entry >= entry_count:
            return None
        (offset,) = _unpack("<I", table, offsets + 4 * entry)
        if offset == NO_INDEX:
            return None

    at = chunk + entries_start + offset
    size, entry_flags = _unpack("<HH", table, at)
    if entry_flags & 0x0008:  # compact entry: type in the flags, data inline
        (data,) = _unpack("<I", table, at + 4)
        return is_default, (entry_flags >> 8, data)
    if entry_flags & 0x0001:  # complex (bag) entry, never a plain string
        return None
    _, _, dtype, data = _unpack("<HBBI", table, at + size)
    return is_default, (dtype, data)
