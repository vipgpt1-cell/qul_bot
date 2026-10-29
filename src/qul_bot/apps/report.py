"""What we tell the team about a build, independent of platform."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from qul_bot.apps.signing import Signing


class Platform(StrEnum):
    ANDROID = "android"
    IOS = "ios"


class Warning(StrEnum):
    """Release mistakes worth a red flag. Each has an i18n text `app.warn.<value>`."""

    DEBUGGABLE = "debuggable"  # android:debuggable="true": anyone can attach a debugger
    DEBUG_SIGNED = "debug_signed"  # signed with the SDK's debug key; Play rejects it
    UNSIGNED = "unsigned"  # will not install
    NO_V2_SIGNATURE = "no_v2"  # v1 only, but targets Android 11+ (required since API 30)
    OLD_TARGET_SDK = "old_target"  # below Google Play's current minimum
    CLEARTEXT = "cleartext"  # usesCleartextTraffic="true": plain HTTP allowed
    CERT_EXPIRED = "cert_expired"
    IOS_DEVELOPMENT = "ios_development"  # development profile (get-task-allow)
    PROFILE_EXPIRED = "profile_expired"
    PROFILE_EXPIRES_SOON = "profile_expires_soon"


@dataclass(slots=True)
class AppReport:
    platform: Platform
    size: int
    name: str | None
    identifier: str | None  # package name / bundle id
    version_name: str | None
    version_code: str | None
    min_os: str | None  # "API 23" / "15.0"
    target_os: str | None
    permissions: list[str] = field(default_factory=list)
    dangerous_permissions: list[str] = field(default_factory=list)
    abis: list[str] = field(default_factory=list)
    signing: Signing | None = None
    #: iOS: development | ad-hoc | enterprise | app-store
    distribution: str | None = None
    team: str | None = None
    profile_expires: datetime | None = None
    devices: int | None = None
    warnings: list[Warning] = field(default_factory=list)
