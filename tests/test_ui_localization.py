import unittest

from tanuki_core.ui_localization import (
    UiTranslationCatalog,
    available_ui_locales,
    character_display_name,
    localize_character_names_in_text,
    normalize_ui_locale,
    set_ui_locale,
    translate_ui,
)


class UiLocalizationTests(unittest.TestCase):
    def test_traditional_chinese_character_names(self):
        expected = {
            "Air Groove": "氣槽",
            "Sirius Symboli": "天狼星叔叔",
            "Symboli Rudolf": "魯道夫象徵",
            "Tokai Teio": "帝寶",
            "Tsurumaru Tsuyoshi": "鶴寶",
        }

        self.assertEqual(
            {
                canonical_name: character_display_name(canonical_name)
                for canonical_name in expected
            },
            expected,
        )

    def test_unknown_names_remain_stable(self):
        self.assertEqual(character_display_name("Future Character"), "Future Character")

    def test_free_form_ui_text_replaces_character_names_and_player(self):
        text = (
            "Symboli Rudolf → Tokai Teio；"
            "Air Groove 與 Sirius Symboli 照顧 Tsurumaru Tsuyoshi。Player 在場。"
        )

        self.assertEqual(
            localize_character_names_in_text(text),
            "魯道夫象徵 → 帝寶；"
            "氣槽 與 天狼星叔叔 照顧 鶴寶。玩家 在場。",
        )

    def test_legacy_chinese_nicknames_follow_selected_display_language(self):
        set_ui_locale("ja_JP")
        try:
            self.assertEqual(
                localize_character_names_in_text(
                    "帝寶、魯道夫、天狼星、鶴寶、氣槽"
                ),
                "トウカイテイオー、シンボリルドルフ、"
                "シリウスシンボリ、ツルマルツヨシ、エアグルーヴ",
            )
        finally:
            set_ui_locale("zh_TW")

    def test_previous_full_chinese_names_convert_to_current_nicknames(self):
        self.assertEqual(
            localize_character_names_in_text(
                "東海帝皇、天狼星象徵與鶴丸強志"
            ),
            "帝寶、天狼星叔叔與鶴寶",
        )

    def test_user_approved_character_names_are_exact_in_all_locales(self):
        expected = {
            "zh_TW": {
                "Tokai Teio": "帝寶",
                "Symboli Rudolf": "魯道夫象徵",
                "Air Groove": "氣槽",
                "Sirius Symboli": "天狼星叔叔",
                "Tsurumaru Tsuyoshi": "鶴寶",
            },
            "zh_CN": {
                "Tokai Teio": "帝宝",
                "Symboli Rudolf": "鲁道夫象征",
                "Air Groove": "气槽",
                "Sirius Symboli": "天狼星叔叔",
                "Tsurumaru Tsuyoshi": "鹤宝",
            },
            "ja_JP": {
                "Tokai Teio": "トウカイテイオー",
                "Symboli Rudolf": "シンボリルドルフ",
                "Air Groove": "エアグルーヴ",
                "Sirius Symboli": "シリウスシンボリ",
                "Tsurumaru Tsuyoshi": "ツルマルツヨシ",
            },
            "en_US": {
                "Tokai Teio": "Tokai Teio",
                "Symboli Rudolf": "Symboli Rudolf",
                "Air Groove": "Air Groove",
                "Sirius Symboli": "Sirius Symboli",
                "Tsurumaru Tsuyoshi": "Tsurumaru Tsuyoshi",
            },
        }

        for locale, names in expected.items():
            with self.subTest(locale=locale):
                self.assertEqual(
                    {
                        name: character_display_name(name, locale=locale)
                        for name in names
                    },
                    names,
                )

    def test_supported_locales_and_aliases_are_stable(self):
        self.assertEqual(
            available_ui_locales(),
            ("zh_TW", "zh_CN", "ja_JP", "en_US"),
        )
        self.assertEqual(normalize_ui_locale("ja-JP"), "ja_JP")
        self.assertEqual(normalize_ui_locale("zh-CN"), "zh_CN")
        self.assertEqual(normalize_ui_locale("unsupported"), "zh_TW")

    def test_simplified_chinese_catalog_localizes_ui_and_legacy_names(self):
        self.assertEqual(
            translate_ui("information_center.title", locale="zh_CN"),
            "狸猫信息中心",
        )
        self.assertEqual(
            localize_character_names_in_text(
                "天狼星舅舅、魯道夫象徵、鶴寶",
                locale="zh_CN",
            ),
            "天狼星叔叔、鲁道夫象征、鹤宝",
        )

    def test_non_default_catalogs_cover_all_english_ui_keys(self):
        catalog = UiTranslationCatalog()

        reference_keys = set(catalog._load("en_US"))
        for locale in ("zh_CN", "ja_JP"):
            with self.subTest(locale=locale):
                self.assertEqual(
                    reference_keys - set(catalog._load(locale)),
                    set(),
                )
        self.assertEqual(
            catalog.translate(
                "achievements.definitions.ambient.tsuyoshi_rare_stand.title",
                locale="zh_CN",
            ),
            "鹤宝站起来了！",
        )

    def test_translation_formats_values_and_falls_back_to_default_locale(self):
        set_ui_locale("en_US")
        try:
            self.assertEqual(
                translate_ui("updates.available", version="0.8.0"),
                "Version 0.8.0 is available.",
            )
            self.assertEqual(
                translate_ui("missing.key", default="Fallback"),
                "Fallback",
            )
        finally:
            set_ui_locale("zh_TW")

    def test_missing_catalog_file_does_not_break_translation(self):
        catalog = UiTranslationCatalog(catalog_dir="missing")
        self.assertEqual(
            catalog.translate("missing.key", default="safe"),
            "safe",
        )


if __name__ == "__main__":
    unittest.main()
