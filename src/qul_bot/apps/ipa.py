"""iOS .ipa inspection: Info.plist and the embedded provisioning profile."""

from __future__ import annotations

import plistlib
import re
import zipfile
from datetime import UTC, datetime, timedelta
from typing import Any

from qul_bot.apps.apk import NotAnApp
from qul_bot.apps.archive import ArchiveError, open_archive, read_entry
from qul_bot.apps.report import AppReport, Platform, Warning

MAX_PLIST = 4 << 20
PROFILE_WARNING_DAYS = 14
_APP_DIR = re.compile(r"^Payload/[^/]+\.app/$")


def _app_dir(archive: zipfile.ZipFile) -> str:
    for info in archive.infolist():
        parts = info.filename.split("/")
        if len(parts) >= 3 and parts[0] == "Payload" and parts[1].endswith(".app"):
            return f"Payload/{parts[1]}/"
    raise NotAnApp("no Payload/*.app")


def _plist(archive: zipfile.ZipFile, name: str) -> dict[str, Any] | None:
    try:
        info = archive.getinfo(name)
    except KeyError:
        return None
    data = read_entry(archive, info, MAX_PLIST)
    if data is None:
        return None
    try:
        value = plistlib.loads(data)
    except (plistlib.InvalidFileException, ValueError, OverflowError):
        return None
    return value if isinstance(value, dict) else None


def _profile(archive: zipfile.ZipFile, app_dir: str) -> dict[str, Any] | None:
    """The provisioning profile is a plist wrapped in a CMS signature; cut the plist out."""
    try:
        info = archive.getinfo(app_dir + "embedded.mobileprovision")
    except KeyError:
        return None
    data = read_entry(archive, info, MAX_PLIST)
    if not data:
        return None
    start, end = data.find(b"<?xml"), data.rfind(b"</plist>")
    if start < 0 or end < start:
        return None
    try:
        value = plistlib.loads(data[start : end + len(b"</plist>")])
    except (plistlib.InvalidFileException, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _distribution(profile: dict[str, Any]) -> str:
    entitlements = profile.get("Entitlements") or {}
    if entitlements.get("get-task-allow") is True:
        return "development"
    if profile.get("ProvisionsAllDevices") is True:
        return "enterprise"
    if profile.get("ProvisionedDevices"):
        return "ad-hoc"
    return "app-store"


def inspect_ipa(data: bytes, now: datetime | None = None) -> AppReport:
    now = now or datetime.now(UTC)
    try:
        archive = open_archive(data)
    except ArchiveError as exc:
        raise NotAnApp("not a zip archive") from exc
    app_dir = _app_dir(archive)
    info = _plist(archive, app_dir + "Info.plist")
    if info is None:
        raise NotAnApp("no readable Info.plist")

    def text(key: str) -> str | None:
        value = info.get(key)
        return str(value) if value not in (None, "") else None

    report = AppReport(
        platform=Platform.IOS,
        size=len(data),
        name=text("CFBundleDisplayName") or text("CFBundleName"),
        identifier=text("CFBundleIdentifier"),
        version_name=text("CFBundleShortVersionString"),
        version_code=text("CFBundleVersion"),
        min_os=f"iOS {info['MinimumOSVersion']}" if info.get("MinimumOSVersion") else None,
        target_os=f"iOS SDK {info['DTPlatformVersion']}" if info.get("DTPlatformVersion") else None,
    )

    profile = _profile(archive, app_dir)
    if profile is not None:
        report.distribution = _distribution(profile)
        report.team = str(profile.get("TeamName") or "") or None
        devices = profile.get("ProvisionedDevices")
        report.devices = len(devices) if isinstance(devices, list) else None
        expires = profile.get("ExpirationDate")
        if isinstance(expires, datetime):
            expires = expires if expires.tzinfo else expires.replace(tzinfo=UTC)
            report.profile_expires = expires
            if expires < now:
                report.warnings.append(Warning.PROFILE_EXPIRED)
            elif expires - now < timedelta(days=PROFILE_WARNING_DAYS):
                report.warnings.append(Warning.PROFILE_EXPIRES_SOON)
        if report.distribution == "development":
            report.warnings.append(Warning.IOS_DEVELOPMENT)
    return report


def inspect_build(file_name: str, data: bytes, now: datetime | None = None) -> AppReport:
    """Dispatch on the file name: .apk or .ipa."""
    from qul_bot.apps.apk import inspect_apk

    lowered = file_name.lower()
    if lowered.endswith(".apk"):
        return inspect_apk(data, now)
    if lowered.endswith(".ipa"):
        return inspect_ipa(data, now)
    raise NotAnApp("unsupported file type")
