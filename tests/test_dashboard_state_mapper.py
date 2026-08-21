import unittest

from tanuki_core.dashboard_state_mapper import (
    DashboardConfigState,
    DashboardOptionBounds,
    apply_dashboard_config_to_settings,
    build_dashboard_config_state,
    build_pet_config_state,
    dashboard_config_state_to_payload,
    normalize_dashboard_config_state,
    normalize_pet_config_state,
    pet_config_state_to_payload,
    safe_index,
)
from tanuki_core.settings_provider import RuntimeSettings
from tanuki_core.information_center_size_rules import SIZE_16_10
from tanuki_core.information_center_spec import PAGE_EVENT_LOG
from tanuki_core.information_center_state import (
    build_information_center_config_state,
)


class DashboardStateMapperTests(unittest.TestCase):
    def test_safe_index_clamps_and_falls_back(self):
        self.assertEqual(safe_index("2", 0, 5), 2)
        self.assertEqual(safe_index("99", 1, 5), 4)
        self.assertEqual(safe_index("oops", 3, 5), 3)

    def test_normalize_dashboard_config_state_uses_bounds(self):
        defaults = DashboardConfigState(
            world_mode="golden_legend",
            care_feature_enabled=True,
            teio_dur_idx=3,
            tsuyoshi_dur_idx=2,
            time_scale_idx=0,
            display_scale_idx=0,
            debug_enabled=False,
        )
        bounds = DashboardOptionBounds(
            teio_duration_count=5,
            tsuyoshi_duration_count=5,
            time_scale_count=4,
            display_scale_count=4,
        )

        state = normalize_dashboard_config_state(
            {
                "care_feature_enabled": False,
                "world_mode": "sandbox",
                "teio_dur_idx": 99,
                "tsuyoshi_dur_idx": "1",
                "time_scale_idx": "bad",
                "display_scale_idx": 2,
                "debug_enabled": True,
                "social_status_enabled": True,
            },
            defaults=defaults,
            option_bounds=bounds,
        )

        self.assertEqual(state.world_mode, "sandbox")
        self.assertFalse(state.care_feature_enabled)
        self.assertEqual(state.teio_dur_idx, 4)
        self.assertEqual(state.tsuyoshi_dur_idx, 1)
        self.assertEqual(state.time_scale_idx, 0)
        self.assertEqual(state.display_scale_idx, 2)
        self.assertTrue(state.debug_enabled)
        self.assertTrue(state.social_status_enabled)

    def test_apply_dashboard_config_to_settings_updates_provider(self):
        settings = RuntimeSettings()
        state = build_dashboard_config_state(
            world_mode="sandbox",
            care_feature_enabled=False,
            teio_dur_idx=1,
            tsuyoshi_dur_idx=4,
            time_scale_idx=2,
            display_scale_idx=3,
            debug_enabled=True,
            social_status_enabled=True,
            race_frequency="frequent",
            chorus_frequency="occasional",
            mood_climate="expressive",
            ui_locale="ja_JP",
        )

        apply_dashboard_config_to_settings(settings, state)

        self.assertEqual(settings.world_mode, "sandbox")
        self.assertFalse(settings.care_feature_enabled)
        self.assertEqual(settings.teio_dur_idx, 1)
        self.assertEqual(settings.tsuyoshi_dur_idx, 4)
        self.assertEqual(settings.time_scale_idx, 2)
        self.assertEqual(settings.display_scale_idx, 3)
        self.assertTrue(settings.debug_enabled)
        self.assertTrue(settings.social_status_enabled)
        self.assertEqual(settings.race_frequency, "frequent")
        self.assertEqual(settings.chorus_frequency, "occasional")
        self.assertEqual(settings.mood_climate, "expressive")
        self.assertEqual(settings.ui_locale, "ja_JP")

    def test_dashboard_payload_round_trip_uses_expected_shape(self):
        state = build_dashboard_config_state(
            world_mode="golden_legend",
            care_feature_enabled=True,
            teio_dur_idx=2,
            tsuyoshi_dur_idx=3,
            time_scale_idx=1,
            display_scale_idx=0,
            debug_enabled=False,
            social_status_enabled=True,
            information_center=build_information_center_config_state(
                x=120,
                y=80,
                width=960,
                height=640,
                page_id=PAGE_EVENT_LOG,
                size_preset_id=SIZE_16_10,
            ),
        )

        payload = dashboard_config_state_to_payload(state)

        self.assertEqual(
            payload,
            {
                "world_mode": "golden_legend",
                "care_feature_enabled": True,
                "teio_dur_idx": 2,
                "tsuyoshi_dur_idx": 3,
                "time_scale_idx": 1,
                "display_scale_idx": 0,
                "debug_enabled": False,
                "social_status_enabled": True,
                "race_frequency": "normal",
                "chorus_frequency": "normal",
                "mood_climate": "cheerful",
                "ui_locale": "zh_TW",
                "information_center": {
                    "x": 120,
                    "y": 80,
                    "width": 960,
                    "height": 640,
                    "page_id": "event_log",
                    "size_preset_id": "comfortable_16_10",
                },
            },
        )

    def test_pet_config_state_normalizes_and_serializes(self):
        defaults = build_pet_config_state(x=100, y=200, user_visible=True)
        state = normalize_pet_config_state(
            {"x": "320", "y": 480, "user_visible": 0},
            defaults=defaults,
        )

        self.assertEqual(state.x, 320)
        self.assertEqual(state.y, 480)
        self.assertFalse(state.user_visible)
        self.assertEqual(
            pet_config_state_to_payload(state),
            {"x": 320, "y": 480, "user_visible": False},
        )

    def test_pet_config_state_falls_back_when_coordinates_are_invalid(self):
        defaults = build_pet_config_state(x=100, y=200, user_visible=True)

        state = normalize_pet_config_state(
            {"x": "bad", "y": None, "user_visible": True},
            defaults=defaults,
        )

        self.assertEqual(state.x, 100)
        self.assertEqual(state.y, 200)


if __name__ == "__main__":
    unittest.main()
