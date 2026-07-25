import unittest

from tanuki_core.information_center_size_rules import (
    INFORMATION_CENTER_SIZE_PRESETS,
    SIZE_4_3,
    SIZE_COMPACT,
    fit_window_size_for_preset,
    get_information_center_size_preset,
)


class InformationCenterSizeRulesTests(unittest.TestCase):
    def test_presets_have_unique_ids_and_positive_scene_sizes(self):
        self.assertEqual(
            len({preset.preset_id for preset in INFORMATION_CENTER_SIZE_PRESETS}),
            len(INFORMATION_CENTER_SIZE_PRESETS),
        )
        self.assertTrue(all(min(preset.scene_size) > 0 for preset in INFORMATION_CENTER_SIZE_PRESETS))

    def test_fit_keeps_scene_ratio_and_adds_navigation_height(self):
        preset = get_information_center_size_preset(SIZE_4_3)

        width, height = fit_window_size_for_preset(
            preset,
            available_size=(1920, 1080),
            navigation_height=62,
        )

        self.assertEqual((width, height), (1200, 962))
        self.assertAlmostEqual(width / (height - 62), 4.0 / 3.0, places=3)

    def test_fit_scales_down_to_available_screen(self):
        preset = get_information_center_size_preset(SIZE_4_3)

        width, height = fit_window_size_for_preset(
            preset,
            available_size=(1000, 760),
            navigation_height=60,
            screen_margin=40,
        )

        self.assertLessEqual(width, 920)
        self.assertLessEqual(height, 680)

    def test_compact_preset_explicitly_uses_whiteboard_crop_mode(self):
        preset = get_information_center_size_preset(SIZE_COMPACT)

        self.assertEqual(preset.scene_size, (720, 420))
        self.assertIn("裁切", preset.label)


if __name__ == "__main__":
    unittest.main()
