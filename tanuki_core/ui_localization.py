from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping


DEFAULT_UI_LOCALE = "zh_TW"
SUPPORTED_UI_LOCALES = ("zh_TW", "zh_CN", "ja_JP", "en_US")
UI_LOCALE_ALIASES = {
    "zh-tw": "zh_TW",
    "zh_tw": "zh_TW",
    "zh-cn": "zh_CN",
    "zh_cn": "zh_CN",
    "ja-jp": "ja_JP",
    "ja_jp": "ja_JP",
    "en-us": "en_US",
    "en_us": "en_US",
}


def normalize_ui_locale(locale, default=DEFAULT_UI_LOCALE):
    value = str(locale or "").strip()
    if value in SUPPORTED_UI_LOCALES:
        return value
    normalized_alias = UI_LOCALE_ALIASES.get(value.lower())
    if normalized_alias:
        return normalized_alias
    return str(default)


def _flatten_catalog(raw, prefix=""):
    flattened = {}
    for key, value in raw.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, Mapping):
            flattened.update(_flatten_catalog(value, path))
        elif isinstance(value, str):
            flattened[path] = value
    return flattened


class UiTranslationCatalog:
    """Load keyed UI resources while keeping runtime identifiers canonical."""

    def __init__(self, catalog_dir=None, default_locale=DEFAULT_UI_LOCALE):
        if catalog_dir is None:
            if getattr(sys, "frozen", False) and getattr(sys, "_MEIPASS", ""):
                resource_root = str(sys._MEIPASS)
            else:
                resource_root = os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__))
                )
            catalog_dir = os.path.join(resource_root, "UI", "locales")
        self.catalog_dir = str(
            catalog_dir
        )
        self.default_locale = normalize_ui_locale(default_locale)
        self._catalogs = {}

    def available_locales(self):
        return SUPPORTED_UI_LOCALES

    def _load(self, locale):
        locale = normalize_ui_locale(locale)
        if locale in self._catalogs:
            return self._catalogs[locale]
        path = os.path.join(self.catalog_dir, f"{locale}.json")
        try:
            with open(path, "r", encoding="utf-8") as stream:
                raw = json.load(stream)
            if not isinstance(raw, dict):
                raise ValueError("locale catalog root must be an object")
            catalog = _flatten_catalog(raw)
        except (OSError, ValueError, json.JSONDecodeError):
            catalog = {}
        self._catalogs[locale] = catalog
        return catalog

    def translate(self, key, *, locale=None, default=None, **values):
        normalized_locale = normalize_ui_locale(locale or self.default_locale)
        key = str(key or "")
        text = self._load(normalized_locale).get(key)
        if text is None and normalized_locale != self.default_locale:
            text = self._load(self.default_locale).get(key)
        if text is None:
            text = str(default if default is not None else key)
        if not values:
            return text
        try:
            return text.format(**values)
        except (KeyError, ValueError):
            return text


_SHARED_CATALOG = UiTranslationCatalog()
_current_ui_locale = DEFAULT_UI_LOCALE


def available_ui_locales():
    return _SHARED_CATALOG.available_locales()


def get_ui_locale():
    return _current_ui_locale


def set_ui_locale(locale):
    global _current_ui_locale
    _current_ui_locale = normalize_ui_locale(locale)
    return _current_ui_locale


def translate_ui(key, *, locale=None, default=None, **values):
    return _SHARED_CATALOG.translate(
        key,
        locale=locale or get_ui_locale(),
        default=default,
        **values,
    )


def character_display_name(character_name, locale=None):
    """Return a localized label without changing the canonical runtime name."""

    canonical_name = str(character_name or "")
    return translate_ui(
        f"characters.{canonical_name}",
        locale=locale,
        default=canonical_name,
    )


def localize_character_names_in_text(text, locale=None):
    """Replace canonical and legacy nicknames in user-facing free-form text."""

    localized_text = str(text or "")
    display_names = {
        canonical_name: character_display_name(canonical_name, locale=locale)
        for canonical_name in (
            "Tsurumaru Tsuyoshi",
            "Symboli Rudolf",
            "Sirius Symboli",
            "Tokai Teio",
            "Air Groove",
            "Player",
        )
    }
    placeholders = {}
    for index, display_name in enumerate(
        sorted(set(display_names.values()), key=len, reverse=True)
    ):
        placeholder = f"\0tanuki_name_{index}\0"
        if display_name:
            localized_text = localized_text.replace(display_name, placeholder)
            placeholders[placeholder] = display_name

    legacy_aliases = {
        "鶴丸強志": "Tsurumaru Tsuyoshi",
        "天狼星象徵": "Sirius Symboli",
        "天狼星舅舅": "Sirius Symboli",
        "天狼星叔叔": "Sirius Symboli",
        "東海帝皇": "Tokai Teio",
        "魯道夫象徵": "Symboli Rudolf",
        "鶴寶": "Tsurumaru Tsuyoshi",
        "魯道夫": "Symboli Rudolf",
        "天狼星": "Sirius Symboli",
        "帝寶": "Tokai Teio",
        "氣槽": "Air Groove",
        "鹤丸强志": "Tsurumaru Tsuyoshi",
        "天狼星象征": "Sirius Symboli",
        "东海帝皇": "Tokai Teio",
        "鲁道夫象征": "Symboli Rudolf",
        "鹤宝": "Tsurumaru Tsuyoshi",
        "鲁道夫": "Symboli Rudolf",
        "帝宝": "Tokai Teio",
        "气槽": "Air Groove",
    }
    replacement_placeholders = {}
    for index, canonical_name in enumerate(
        sorted(display_names, key=len, reverse=True)
    ):
        placeholder = f"\0tanuki_replacement_{index}\0"
        localized_text = localized_text.replace(canonical_name, placeholder)
        replacement_placeholders[placeholder] = display_names[canonical_name]
    for alias in sorted(legacy_aliases, key=len, reverse=True):
        canonical_name = legacy_aliases[alias]
        placeholder = next(
            token
            for token, display_name in replacement_placeholders.items()
            if display_name == display_names[canonical_name]
        )
        localized_text = localized_text.replace(
            alias,
            placeholder,
        )
    for placeholder, display_name in replacement_placeholders.items():
        localized_text = localized_text.replace(placeholder, display_name)
    for placeholder, display_name in placeholders.items():
        localized_text = localized_text.replace(placeholder, display_name)
    return localized_text
