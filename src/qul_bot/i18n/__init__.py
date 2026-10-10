"""Translations. Add a language by creating `<locale>.py` with a `MESSAGES` dict and
registering it in `CATALOGS`; every key in `uz.py` must exist there (a test enforces it)."""

from __future__ import annotations

from qul_bot.i18n.uz import MESSAGES as UZ

DEFAULT_LOCALE = "uz"
CATALOGS: dict[str, dict[str, str]] = {"uz": UZ}


class _KeepMissing(dict[str, object]):
    """`str.format_map` helper: unknown placeholders stay visible instead of raising."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


class Translator:
    """Looks up a message key in the chosen locale (falling back to the default locale)."""

    def __init__(self, locale: str = DEFAULT_LOCALE) -> None:
        self.locale = locale if locale in CATALOGS else DEFAULT_LOCALE

    def __call__(self, key: str, **params: object) -> str:
        template = CATALOGS[self.locale].get(key) or CATALOGS[DEFAULT_LOCALE].get(key)
        if template is None:
            return key
        return template.format_map(_KeepMissing(params)) if params else template
