"""Android .apk inspection."""

from __future__ import annotations

from datetime import UTC, datetime

from qul_bot.apps.archive import ArchiveError, find, open_archive, read_entry
from qul_bot.apps.binary import BinaryFormatError, Element, Reference, parse_xml, resolve_string
from qul_bot.apps.report import AppReport, Platform, Warning
from qul_bot.apps.signing import read_signing

MAX_MANIFEST = 4 << 20
MAX_RESOURCES = 64 << 20

#: Google Play's minimum targetSdkVersion for app updates (in force since 2025-08-31).
PLAY_MIN_TARGET_SDK = 35
#: APK Signature Scheme v2 is required for apps targeting Android 11 (API 30) and up.
V2_REQUIRED_FROM_SDK = 30

ANDROID_VERSIONS = {
    9: "2.3", 10: "2.3.3", 11: "3.0", 12: "3.1", 13: "3.2", 14: "4.0", 15: "4.0.3",
    16: "4.1", 17: "4.2", 18: "4.3", 19: "4.4", 20: "4.4W", 21: "5.0", 22: "5.1",
    23: "6.0", 24: "7.0", 25: "7.1", 26: "8.0", 27: "8.1", 28: "9", 29: "10", 30: "11",
    31: "12", 32: "12L", 33: "13", 34: "14", 35: "15", 36: "16",
}  # fmt: skip

#: Runtime ("dangerous") permissions plus a few special ones stores look at closely.
SENSITIVE_PERMISSIONS = frozenset(
    "android.permission." + p
    for p in (
        "READ_CALENDAR", "WRITE_CALENDAR", "CAMERA", "READ_CONTACTS", "WRITE_CONTACTS",
        "GET_ACCOUNTS", "ACCESS_FINE_LOCATION", "ACCESS_COARSE_LOCATION",
        "ACCESS_BACKGROUND_LOCATION", "RECORD_AUDIO", "READ_PHONE_STATE", "READ_PHONE_NUMBERS",
        "CALL_PHONE", "ANSWER_PHONE_CALLS", "READ_CALL_LOG", "WRITE_CALL_LOG", "ADD_VOICEMAIL",
        "USE_SIP", "PROCESS_OUTGOING_CALLS", "BODY_SENSORS", "BODY_SENSORS_BACKGROUND",
        "ACTIVITY_RECOGNITION", "SEND_SMS", "RECEIVE_SMS", "READ_SMS", "RECEIVE_WAP_PUSH",
        "RECEIVE_MMS", "READ_EXTERNAL_STORAGE", "WRITE_EXTERNAL_STORAGE",
        "ACCESS_MEDIA_LOCATION", "READ_MEDIA_IMAGES", "READ_MEDIA_VIDEO", "READ_MEDIA_AUDIO",
        "READ_MEDIA_VISUAL_USER_SELECTED", "POST_NOTIFICATIONS", "NEARBY_WIFI_DEVICES",
        "BLUETOOTH_SCAN", "BLUETOOTH_CONNECT", "BLUETOOTH_ADVERTISE", "UWB_RANGING",
        "SYSTEM_ALERT_WINDOW", "REQUEST_INSTALL_PACKAGES", "MANAGE_EXTERNAL_STORAGE",
        "QUERY_ALL_PACKAGES", "READ_PRIVILEGED_PHONE_STATE", "BIND_ACCESSIBILITY_SERVICE",
    )
)  # fmt: skip


class NotAnApp(ValueError):
    """The file is not a build we can read."""


def android_version(sdk: object) -> str | None:
    """`API 23 (Android 6.0)`; codenames and unknown levels are shown as they are."""
    if sdk is None:
        return None
    if isinstance(sdk, int):
        name = ANDROID_VERSIONS.get(sdk)
        return f"API {sdk} (Android {name})" if name else f"API {sdk}"
    return str(sdk)


def _sdk(element: Element | None, name: str) -> int | str | None:
    if element is None:
        return None
    value = element.attrs.get(name)
    return value if isinstance(value, int | str) and not isinstance(value, bool) else None


def inspect_apk(data: bytes, now: datetime | None = None) -> AppReport:
    now = now or datetime.now(UTC)
    try:
        archive = open_archive(data)
    except ArchiveError as exc:
        raise NotAnApp("not a zip archive") from exc
    manifest_info = find(archive, "AndroidManifest.xml")
    manifest_bytes = read_entry(archive, manifest_info, MAX_MANIFEST) if manifest_info else None
    if manifest_bytes is None:
        raise NotAnApp("no AndroidManifest.xml")
    try:
        manifest = parse_xml(manifest_bytes)
    except (BinaryFormatError, IndexError) as exc:
        raise NotAnApp("unreadable manifest") from exc

    application = manifest.find("application")
    app_attrs = application.attrs if application else {}
    label = app_attrs.get("label")
    if isinstance(label, Reference):
        label = _resolve_label(archive, label.resource_id)
    uses_sdk = manifest.find("uses-sdk")
    min_sdk = _sdk(uses_sdk, "minSdkVersion")
    target_sdk = _sdk(uses_sdk, "targetSdkVersion") or min_sdk

    permissions = sorted(
        {
            str(e.attrs["name"])
            for tag in ("uses-permission", "uses-permission-sdk-23")
            for e in manifest.iter(tag)
            if isinstance(e.attrs.get("name"), str)
        }
    )
    abis = sorted(
        {
            info.filename.split("/")[1]
            for info in archive.infolist()
            if info.filename.startswith("lib/") and info.filename.count("/") >= 2
        }
    )
    signing = read_signing(data, archive)
    version_code = manifest.attrs.get("versionCode")
    version_name = manifest.attrs.get("versionName")

    report = AppReport(
        platform=Platform.ANDROID,
        size=len(data),
        name=label if isinstance(label, str) and label else None,
        identifier=str(manifest.attrs.get("package") or "") or None,
        version_name=str(version_name) if version_name is not None else None,
        version_code=str(version_code) if version_code is not None else None,
        min_os=android_version(min_sdk),
        target_os=android_version(target_sdk),
        permissions=permissions,
        dangerous_permissions=[p for p in permissions if p in SENSITIVE_PERMISSIONS],
        abis=abis,
        signing=signing,
    )

    if app_attrs.get("debuggable") is True:
        report.warnings.append(Warning.DEBUGGABLE)
    if app_attrs.get("usesCleartextTraffic") is True:
        report.warnings.append(Warning.CLEARTEXT)
    certificate = signing.certificate
    if not signing.schemes:
        report.warnings.append(Warning.UNSIGNED)
    else:
        if certificate and certificate.is_debug:
            report.warnings.append(Warning.DEBUG_SIGNED)
        if certificate and certificate.not_after and certificate.not_after < now:
            report.warnings.append(Warning.CERT_EXPIRED)
        if (
            signing.schemes == ("v1",)
            and isinstance(target_sdk, int)
            and target_sdk >= V2_REQUIRED_FROM_SDK
        ):
            report.warnings.append(Warning.NO_V2_SIGNATURE)
    if isinstance(target_sdk, int) and target_sdk < PLAY_MIN_TARGET_SDK:
        report.warnings.append(Warning.OLD_TARGET_SDK)
    return report


def _resolve_label(archive: object, resource_id: int) -> str | None:
    import zipfile

    assert isinstance(archive, zipfile.ZipFile)
    info = find(archive, "resources.arsc")
    table = read_entry(archive, info, MAX_RESOURCES) if info else None
    if table is None:
        return None
    try:
        return resolve_string(table, resource_id)
    except (BinaryFormatError, IndexError):
        return None
