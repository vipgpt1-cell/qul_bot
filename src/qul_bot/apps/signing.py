"""APK signatures: v1 (JAR, META-INF/*.RSA|DSA|EC) and v2/v3 (the APK Signing Block)."""

from __future__ import annotations

import hashlib
import struct
import zipfile
from dataclasses import dataclass
from datetime import datetime

from cryptography import x509
from cryptography.hazmat.primitives.serialization import Encoding, pkcs7
from cryptography.x509.oid import NameOID

from qul_bot.apps.archive import read_entry

V2_BLOCK_ID = 0x7109871A
V3_BLOCK_ID = 0xF05368C0
V31_BLOCK_ID = 0x1B93AD61
_BLOCK_MAGIC = b"APK Sig Block 42"
_EOCD_MAGIC = b"PK\x05\x06"
_MAX_CERT_FILE = 1 << 20


@dataclass(frozen=True, slots=True)
class Certificate:
    sha256: str  # hex, lowercase
    subject: str
    common_name: str | None
    not_after: datetime | None

    @property
    def is_debug(self) -> bool:
        """Signed with the Android SDK's auto-generated debug key."""
        return self.common_name == "Android Debug"

    @property
    def fingerprint(self) -> str:
        return ":".join(self.sha256[i : i + 2] for i in range(0, 64, 2)).upper()


@dataclass(frozen=True, slots=True)
class Signing:
    schemes: tuple[str, ...]  # e.g. ("v1", "v2")
    certificate: Certificate | None


def _describe(der: bytes) -> Certificate:
    sha256 = hashlib.sha256(der).hexdigest()
    try:
        cert = x509.load_der_x509_certificate(der)
    except ValueError:
        return Certificate(sha256=sha256, subject="?", common_name=None, not_after=None)
    names = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
    common_name = str(names[0].value) if names else None
    return Certificate(
        sha256=sha256,
        subject=cert.subject.rfc4514_string(),
        common_name=common_name,
        not_after=cert.not_valid_after_utc,
    )


def _v1_certificate(archive: zipfile.ZipFile) -> bytes | None:
    for info in archive.infolist():
        name = info.filename.upper()
        if name.startswith("META-INF/") and name.endswith((".RSA", ".DSA", ".EC")):
            data = read_entry(archive, info, _MAX_CERT_FILE)
            if data is None:
                continue
            try:
                certs = pkcs7.load_der_pkcs7_certificates(data)
            except ValueError:
                continue
            if certs:
                return certs[0].public_bytes(Encoding.DER)
    return None


def _length_prefixed(data: bytes, pos: int) -> tuple[bytes, int]:
    (size,) = struct.unpack_from("<I", data, pos)
    start = pos + 4
    if start + size > len(data):
        raise ValueError("length-prefixed value out of bounds")
    return data[start : start + size], start + size


def _signing_blocks(apk: bytes) -> dict[int, bytes]:
    """Id -> value of every pair in the APK Signing Block (empty if there is none)."""
    eocd = apk.rfind(_EOCD_MAGIC, max(0, len(apk) - 65_557))
    if eocd < 0 or eocd + 20 > len(apk):
        return {}
    (cd_offset,) = struct.unpack_from("<I", apk, eocd + 16)
    if cd_offset < 32 or apk[cd_offset - 16 : cd_offset] != _BLOCK_MAGIC:
        return {}
    (size,) = struct.unpack_from("<Q", apk, cd_offset - 24)
    start = cd_offset - size - 8
    if start < 0 or size > len(apk):
        return {}
    pairs: dict[int, bytes] = {}
    pos, end = start + 8, cd_offset - 24
    while pos + 12 <= end:
        (length,) = struct.unpack_from("<Q", apk, pos)
        if length < 4 or pos + 8 + length > end:
            break
        (block_id,) = struct.unpack_from("<I", apk, pos + 8)
        pairs[block_id] = apk[pos + 12 : pos + 8 + length]
        pos += 8 + length
    return pairs


def _first_certificate(scheme_block: bytes) -> bytes | None:
    """First signer's first certificate in a v2/v3 block."""
    try:
        signers, _ = _length_prefixed(scheme_block, 0)
        signer, _ = _length_prefixed(signers, 0)
        signed_data, _ = _length_prefixed(signer, 0)
        _digests, pos = _length_prefixed(signed_data, 0)
        certificates, _ = _length_prefixed(signed_data, pos)
        certificate, _ = _length_prefixed(certificates, 0)
    except (ValueError, struct.error):
        return None
    return certificate or None


def read_signing(apk: bytes, archive: zipfile.ZipFile) -> Signing:
    schemes: list[str] = []
    certificate_der: bytes | None = None

    blocks = _signing_blocks(apk)
    for block_id, label in ((V31_BLOCK_ID, "v3.1"), (V3_BLOCK_ID, "v3"), (V2_BLOCK_ID, "v2")):
        if block_id in blocks:
            schemes.append(label)
            certificate_der = certificate_der or _first_certificate(blocks[block_id])

    v1 = _v1_certificate(archive)
    if v1 is not None:
        schemes.append("v1")
        certificate_der = certificate_der or v1

    order = {"v1": 0, "v2": 1, "v3": 2, "v3.1": 3}
    return Signing(
        schemes=tuple(sorted(schemes, key=order.__getitem__)),
        certificate=_describe(certificate_der) if certificate_der else None,
    )
