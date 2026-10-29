"""App build inspection, checked against values read independently with androguard."""

from __future__ import annotations

import contextlib
import io
import plistlib
import random
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from qul_bot.apps.apk import NotAnApp, android_version, inspect_apk
from qul_bot.apps.binary import BinaryFormatError, parse_xml, resolve_string
from qul_bot.apps.ipa import inspect_build, inspect_ipa
from qul_bot.apps.report import Platform, Warning
from tests.axml_writer import Node, encode

FIXTURES = Path(__file__).parent / "fixtures" / "apk"
NOW = datetime(2026, 10, 29, tzinfo=UTC)
GOLDEN_CERT = "fb5dbd3c669af9fc236c6991e6387b7f11ff0590997f22d0f5c74ff40e04fca8"


def apk(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


# ---- reference values (androguard) ----------------------------------------------------


@pytest.mark.parametrize(
    ("name", "schemes"),
    [
        ("golden-aligned-v1-out.apk", ("v1",)),
        ("golden-aligned-v2-out.apk", ("v2",)),
        ("golden-aligned-v1v2-out.apk", ("v1", "v2")),
        ("golden-unaligned-v3-out.apk", ("v3",)),
        ("weird-compression-method.apk", ("v1",)),
    ],
)
def test_signature_schemes_and_certificate(name: str, schemes: tuple[str, ...]) -> None:
    report = inspect_apk(apk(name), NOW)
    assert report.signing is not None
    assert report.signing.schemes == schemes
    assert report.signing.certificate is not None
    assert report.signing.certificate.sha256 == GOLDEN_CERT
    assert report.signing.certificate.common_name == "rsa-2048"
    assert report.name == "Tiny App for CTS"  # resolved through resources.arsc
    assert (report.identifier, report.version_name, report.version_code) == (
        "android.appsecurity.cts.tinyapp", "1.0", "10",
    )  # fmt: skip
    assert report.min_os == "API 23 (Android 6.0)"


def test_ecdsa_v2_certificate() -> None:
    report = inspect_apk(apk("v2-only-with-ecdsa-sha256-p256.apk"), NOW)
    assert report.signing is not None and report.signing.certificate is not None
    assert report.signing.certificate.sha256 == (
        "6a8b96e278e58f62cfe3584022cec1d0527fcb85a9e5d2e1694eb0405be5b599"
    )


def test_debug_build_is_flagged() -> None:
    report = inspect_apk(apk("TestActivity.apk"), NOW)
    assert (report.name, report.identifier) == ("TestsAndroguardApplication", "tests.androguard")
    assert report.min_os == "API 9 (Android 2.3)"
    assert report.target_os == "API 16 (Android 4.1)"
    assert Warning.DEBUGGABLE in report.warnings
    assert Warning.DEBUG_SIGNED in report.warnings
    assert report.signing is not None and report.signing.certificate is not None
    assert report.signing.certificate.sha256.startswith("6f5c31608f1f")


def test_debug_key_and_expired_certificate() -> None:
    report = inspect_apk(apk("Test-debug.apk"), NOW)
    assert report.name == "TestActivity"
    assert {Warning.DEBUG_SIGNED, Warning.CERT_EXPIRED} <= set(report.warnings)


def test_unresolvable_label_and_unsigned() -> None:
    report = inspect_apk(apk("AndroidManifest_ShortName.apk"), NOW)
    assert report.identifier == "com.android.galaxy4"
    assert report.name is None  # androguard cannot resolve it either
    assert Warning.UNSIGNED in report.warnings


def test_release_mistakes_in_synthetic_build() -> None:
    report = inspect_apk(apk("synthetic-v1-target34.apk"), NOW)
    assert (report.name, report.version_name, report.version_code) == ("Qul Sample", "2.1.0", "42")
    assert report.target_os == "API 34 (Android 14)"
    assert report.abis == ["arm64-v8a"]
    assert report.permissions == [
        "android.permission.ACCESS_FINE_LOCATION",
        "android.permission.CAMERA",
        "android.permission.INTERNET",
    ]
    assert report.dangerous_permissions == [
        "android.permission.ACCESS_FINE_LOCATION",
        "android.permission.CAMERA",
    ]
    assert report.warnings == [Warning.CLEARTEXT, Warning.NO_V2_SIGNATURE, Warning.OLD_TARGET_SDK]
    assert report.signing is not None and report.signing.certificate is not None
    assert report.signing.certificate.common_name == "Qul Test Release"


def test_android_version_names() -> None:
    assert android_version(35) == "API 35 (Android 15)"
    assert android_version(99) == "API 99"
    assert android_version("Baklava") == "Baklava"
    assert android_version(None) is None


# ---- hostile input --------------------------------------------------------------------


def _zip(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    return buffer.getvalue()


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"not a zip at all",
        _zip({"hello.txt": b"hi"}),
        _zip({"AndroidManifest.xml": b"<manifest/>"}),  # text XML, not binary
        _zip({"AndroidManifest.xml": b"\x03\x00\x08\x00\xff\xff\xff\xff"}),
    ],
)
def test_garbage_is_rejected_cleanly(data: bytes) -> None:
    with pytest.raises(NotAnApp):
        inspect_apk(data, NOW)


def test_zip_bomb_is_not_inflated() -> None:
    bomb = io.BytesIO()
    with zipfile.ZipFile(bomb, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("AndroidManifest.xml", b"\0" * (64 << 20))  # 64 MB of zeros
    assert len(bomb.getvalue()) < 1 << 20
    with pytest.raises(NotAnApp):
        inspect_apk(bomb.getvalue(), NOW)


@pytest.mark.parametrize("seed", range(4))
def test_fuzzed_manifests_never_crash(seed: int) -> None:
    """Flip random bytes in a real manifest and resource table: only NotAnApp may escape."""
    rng = random.Random(seed)
    original = zipfile.ZipFile(FIXTURES / "golden-aligned-v1v2-out.apk")
    manifest = original.read("AndroidManifest.xml")
    table = original.read("resources.arsc")
    for _ in range(250):
        broken_manifest, broken_table = bytearray(manifest), bytearray(table)
        for target in (broken_manifest, broken_table):
            for _ in range(rng.randint(1, 8)):
                target[rng.randrange(len(target))] = rng.randrange(256)
        data = _zip({"AndroidManifest.xml": bytes(broken_manifest),
                     "resources.arsc": bytes(broken_table)})  # fmt: skip
        with contextlib.suppress(NotAnApp):
            inspect_apk(data, NOW)


def test_binary_parsers_raise_their_own_error() -> None:
    with pytest.raises(BinaryFormatError):
        parse_xml(b"\x02\x00\x08\x00\x08\x00\x00\x00")
    with pytest.raises(BinaryFormatError):
        resolve_string(b"\x03\x00\x08\x00\x08\x00\x00\x00", 0x7F010000)


def test_encoder_round_trip() -> None:
    root = parse_xml(encode(Node("manifest", {"package": "a.b", "versionCode": 7},
                                [Node("application", {"debuggable": True})])))  # fmt: skip
    assert root.attrs == {"package": "a.b", "versionCode": 7}
    application = root.find("application")
    assert application is not None and application.attrs == {"debuggable": True}


# ---- iOS ------------------------------------------------------------------------------


def make_ipa(
    *, development: bool = False, devices: int = 0, expires: datetime | None = None
) -> bytes:
    info = {
        "CFBundleDisplayName": "Qul iOS",
        "CFBundleIdentifier": "uz.qul.app",
        "CFBundleShortVersionString": "1.4.0",
        "CFBundleVersion": "120",
        "MinimumOSVersion": "15.0",
        "DTPlatformVersion": "18.2",
    }
    profile = {
        "TeamName": "Qul LLC",
        "ExpirationDate": (expires or datetime(2027, 6, 1)).replace(tzinfo=None),
        "Entitlements": {"get-task-allow": development},
    }
    if devices:
        profile["ProvisionedDevices"] = [f"device-{i}" for i in range(devices)]
    signed_profile = b"\x30\x82junk-cms-header" + plistlib.dumps(profile) + b"\x00trailing-sig"
    return _zip({
        "Payload/Qul.app/Info.plist": plistlib.dumps(info, fmt=plistlib.FMT_BINARY),
        "Payload/Qul.app/embedded.mobileprovision": signed_profile,
        "Payload/Qul.app/Qul": b"\xcf\xfa\xed\xfe",
    })  # fmt: skip


def test_ipa_store_build() -> None:
    report = inspect_ipa(make_ipa(), NOW)
    assert report.platform is Platform.IOS
    assert (report.name, report.identifier) == ("Qul iOS", "uz.qul.app")
    assert (report.version_name, report.version_code) == ("1.4.0", "120")
    assert (report.min_os, report.target_os) == ("iOS 15.0", "iOS SDK 18.2")
    assert (report.distribution, report.team) == ("app-store", "Qul LLC")
    assert report.warnings == []


def test_ipa_development_and_ad_hoc_profiles() -> None:
    development = inspect_ipa(make_ipa(development=True, devices=3), NOW)
    assert development.distribution == "development"
    assert development.devices == 3
    assert Warning.IOS_DEVELOPMENT in development.warnings
    ad_hoc = inspect_ipa(make_ipa(devices=12), NOW)
    assert ad_hoc.distribution == "ad-hoc"


def test_ipa_profile_expiry() -> None:
    expired = inspect_ipa(make_ipa(expires=datetime(2026, 10, 1)), NOW)
    assert Warning.PROFILE_EXPIRED in expired.warnings
    soon = inspect_ipa(make_ipa(expires=datetime(2026, 11, 5)), NOW)
    assert Warning.PROFILE_EXPIRES_SOON in soon.warnings


def test_ipa_without_payload_is_rejected() -> None:
    with pytest.raises(NotAnApp):
        inspect_ipa(_zip({"Info.plist": b"x"}), NOW)


def test_dispatch_by_extension() -> None:
    assert inspect_build("Build.APK", apk("golden-aligned-v1-out.apk"), NOW).platform is (
        Platform.ANDROID
    )
    assert inspect_build("app.ipa", make_ipa(), NOW).platform is Platform.IOS
    with pytest.raises(NotAnApp):
        inspect_build("notes.pdf", b"%PDF", NOW)
