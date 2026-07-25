import unittest

from tanuki_core.ui_localization import (
    character_display_name,
    localize_character_names_in_text,
)


class UiLocalizationTests(unittest.TestCase):
    def test_traditional_chinese_character_names(self):
        expected = {
            "Air Groove": "氣槽",
            "Sirius Symboli": "天狼星象徵",
            "Symboli Rudolf": "魯道夫象徵",
            "Tokai Teio": "東海帝皇",
            "Tsurumaru Tsuyoshi": "鶴丸強志",
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
            "魯道夫象徵 → 東海帝皇；"
            "氣槽 與 天狼星象徵 照顧 鶴丸強志。玩家 在場。",
        )

    def test_explicit_unsupported_locale_falls_back_to_canonical_name(self):
        self.assertEqual(
            character_display_name("Tokai Teio", locale="ja_JP"),
            "Tokai Teio",
        )


if __name__ == "__main__":
    unittest.main()
