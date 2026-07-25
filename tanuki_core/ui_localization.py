from __future__ import annotations


DEFAULT_UI_LOCALE = "zh_TW"

CHARACTER_DISPLAY_NAMES = {
    "zh_TW": {
        "Air Groove": "氣槽",
        "Sirius Symboli": "天狼星象徵",
        "Symboli Rudolf": "魯道夫象徵",
        "Tokai Teio": "東海帝皇",
        "Tsurumaru Tsuyoshi": "鶴丸強志",
        "Player": "玩家",
    },
}


def character_display_name(character_name, locale=DEFAULT_UI_LOCALE):
    """Return a localized label without changing the canonical runtime name."""

    canonical_name = str(character_name or "")
    return CHARACTER_DISPLAY_NAMES.get(str(locale or ""), {}).get(
        canonical_name,
        canonical_name,
    )


def localize_character_names_in_text(text, locale=DEFAULT_UI_LOCALE):
    """Replace canonical character names inside user-facing free-form text."""

    localized_text = str(text or "")
    display_names = CHARACTER_DISPLAY_NAMES.get(str(locale or ""), {})
    for canonical_name in sorted(display_names, key=len, reverse=True):
        localized_text = localized_text.replace(
            canonical_name,
            display_names[canonical_name],
        )
    return localized_text
