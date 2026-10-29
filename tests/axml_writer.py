"""A tiny encoder for Android binary XML, used to build test manifests.

Only what the tests need: UTF-16 string pool, resource map, elements with typed attributes.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field

from qul_bot.apps.binary import ATTRIBUTE_IDS, TYPE_BOOLEAN, TYPE_INT_DEC, TYPE_STRING

ANDROID_NS = "http://schemas.android.com/apk/res/android"
_IDS = {name: rid for rid, name in ATTRIBUTE_IDS.items()}
NONE = 0xFFFFFFFF


@dataclass
class Node:
    name: str
    attrs: dict[str, str | int | bool] = field(default_factory=dict)
    children: list[Node] = field(default_factory=list)


def _walk(node: Node) -> list[Node]:
    return [node, *(n for child in node.children for n in _walk(child))]


def encode(root: Node) -> bytes:
    nodes = _walk(root)
    attr_names = list(dict.fromkeys(a for n in nodes for a in n.attrs))
    # Attributes with framework ids must come first: the resource map is index-aligned.
    known = [a for a in attr_names if a in _IDS]
    other = [a for a in attr_names if a not in _IDS]
    strings: list[str] = [*known, *other, "android", ANDROID_NS]
    for node in nodes:
        for value in (node.name, *(v for v in node.attrs.values() if isinstance(v, str))):
            if value not in strings:
                strings.append(value)
    index = {s: i for i, s in enumerate(strings)}

    body = bytearray()
    for s in strings:
        encoded = s.encode("utf-16-le")
        body += struct.pack("<H", len(s)) + encoded + b"\x00\x00"
    while len(body) % 4:
        body += b"\x00"
    offsets, pos = [], 0
    for s in strings:
        offsets.append(pos)
        pos += 2 + 2 * len(s) + 2
    header = 28
    strings_start = header + 4 * len(strings)
    pool = struct.pack(
        "<HHIIIIII", 0x0001, header, strings_start + len(body), len(strings), 0, 0,
        strings_start, 0,
    ) + struct.pack(f"<{len(strings)}I", *offsets) + bytes(body)  # fmt: skip

    resource_map = struct.pack("<HHI", 0x0180, 8, 8 + 4 * len(known)) + struct.pack(
        f"<{len(known)}I", *(_IDS[a] for a in known)
    )
    namespace = struct.pack(
        "<HHIIIII", 0x0100, 16, 24, 1, NONE, index["android"], index[ANDROID_NS]
    )

    def element(node: Node) -> bytes:
        attrs = bytearray()
        for name, value in node.attrs.items():
            if isinstance(value, bool):
                raw, dtype, data = NONE, TYPE_BOOLEAN, 0xFFFFFFFF if value else 0
            elif isinstance(value, int):
                raw, dtype, data = NONE, TYPE_INT_DEC, value & 0xFFFFFFFF
            else:
                raw, dtype, data = index[value], TYPE_STRING, index[value]
            ns = index[ANDROID_NS] if name in _IDS else NONE
            attrs += struct.pack("<IIIHBBI", ns, index[name], raw, 8, 0, dtype, data)
        ext = struct.pack("<IIHHHHHH", NONE, index[node.name], 20, 20, len(node.attrs), 0, 0, 0)
        start_size = 16 + len(ext) + len(attrs)
        start = struct.pack("<HHIII", 0x0102, 16, start_size, 1, NONE) + ext + bytes(attrs)
        end = struct.pack("<HHIIIII", 0x0103, 16, 24, 1, NONE, NONE, index[node.name])
        return start + b"".join(element(c) for c in node.children) + end

    content = pool + resource_map + namespace + element(root)
    return struct.pack("<HHI", 0x0003, 8, 8 + len(content)) + content
