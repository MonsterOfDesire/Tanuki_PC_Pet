import unittest

from tanuki_core.config_rules import (
    CONFIG_SCHEMA_VERSION,
    migrate_config_state,
    normalize_config_state,
    resolve_config_autosave_target,
)


class ConfigRuleTests(unittest.TestCase):
    def test_resolve_config_autosave_target_skips_provider_when_disabled(self):
        provider_calls = []

        target = resolve_config_autosave_target(
            lambda: provider_calls.append(True),
            autosave_enabled=False,
        )

        self.assertIsNone(target)
        self.assertEqual(provider_calls, [])

    def test_resolve_config_autosave_target_returns_available_store(self):
        store = object()

        target = resolve_config_autosave_target(
            lambda: store,
            autosave_enabled=True,
        )

        self.assertIs(target, store)

    def test_resolve_config_autosave_target_handles_missing_provider(self):
        self.assertIsNone(
            resolve_config_autosave_target(None, autosave_enabled=True)
        )

    def test_normalize_config_state_upgrades_schema_and_preserves_known_fields(self):
        normalized, warnings = normalize_config_state(
            {
                "schema_version": 1,
                "dashboard": {
                    "world_mode": "sandbox",
                    "care_feature_enabled": False,
                    "debug_enabled": True,
                    "social_status_enabled": True,
                },
                "pets": {
                    "Tokai Teio": {
                        "x": 10,
                        "y": 20,
                        "user_visible": False,
                    },
                },
            }
        )

        self.assertEqual(normalized["schema_version"], CONFIG_SCHEMA_VERSION)
        self.assertEqual(normalized["dashboard"]["world_mode"], "sandbox")
        self.assertFalse(normalized["dashboard"]["care_feature_enabled"])
        self.assertTrue(normalized["dashboard"]["debug_enabled"])
        self.assertTrue(
            normalized["dashboard"]["social_status_enabled"]
        )
        self.assertEqual(normalized["dashboard"]["race_frequency"], "normal")
        self.assertEqual(normalized["dashboard"]["mood_climate"], "cheerful")
        self.assertEqual(normalized["pets"]["Tokai Teio"]["x"], 10)
        self.assertEqual(normalized["household"], {})
        self.assertTrue(any("config schema 1 已升級" in warning for warning in warnings))

    def test_normalize_config_state_resets_invalid_blocks(self):
        normalized, warnings = normalize_config_state(
            {
                "dashboard": [],
                "pets": {
                    "bad": "oops",
                },
            }
        )

        self.assertEqual(normalized["dashboard"]["care_feature_enabled"], True)
        self.assertFalse(
            normalized["dashboard"]["social_status_enabled"]
        )
        self.assertEqual(normalized["pets"], {})
        self.assertEqual(normalized["household"], {})
        self.assertTrue(any("dashboard 區塊不是物件" in warning for warning in warnings))
        self.assertTrue(any("bad: 狀態不是物件" in warning for warning in warnings))

    def test_migrate_config_state_moves_legacy_root_dashboard_fields(self):
        migrated, warnings, original_version = migrate_config_state(
            {
                "care_feature_enabled": False,
                "time_scale_idx": 2,
                "pets": {
                    "Tokai Teio": {"x": 10, "y": 20, "user_visible": True},
                },
            }
        )

        self.assertEqual(original_version, 1)
        self.assertIn("dashboard", migrated)
        self.assertEqual(migrated["dashboard"]["world_mode"], "golden_legend")
        self.assertFalse(migrated["dashboard"]["care_feature_enabled"])
        self.assertEqual(migrated["dashboard"]["time_scale_idx"], 2)
        self.assertEqual(migrated["household"], {})
        self.assertTrue(any("root-level dashboard" in warning for warning in warnings))
        self.assertTrue(any("config schema 1 已升級" in warning for warning in warnings))

    def test_migrate_config_state_warns_on_invalid_schema_version(self):
        migrated, warnings, original_version = migrate_config_state(
            {
                "schema_version": "bad",
                "dashboard": {},
                "pets": {},
            }
        )

        self.assertEqual(migrated["schema_version"], CONFIG_SCHEMA_VERSION)
        self.assertEqual(original_version, 1)
        self.assertTrue(any("schema_version='bad' 無法識別" in warning for warning in warnings))

    def test_migrate_config_state_downgrades_future_schema_to_supported_version(self):
        migrated, warnings, original_version = migrate_config_state(
            {
                "schema_version": 99,
                "dashboard": {"debug_enabled": True, "world_mode": "sandbox"},
                "pets": {},
            }
        )

        self.assertEqual(migrated["schema_version"], CONFIG_SCHEMA_VERSION)
        self.assertEqual(original_version, CONFIG_SCHEMA_VERSION)
        self.assertTrue(any("高於目前支援版本" in warning for warning in warnings))

    def test_normalize_config_state_resets_invalid_household_block(self):
        normalized, warnings = normalize_config_state(
            {
                "household": [],
            }
        )

        self.assertEqual(normalized["household"], {})
        self.assertTrue(any("household 區塊不是物件" in warning for warning in warnings))

    def test_schema_three_config_receives_default_information_center_state(self):
        normalized, warnings = normalize_config_state(
            {
                "schema_version": 3,
                "dashboard": {
                    "world_mode": "golden_legend",
                },
                "pets": {},
                "household": {},
            }
        )

        information_center = normalized["dashboard"]["information_center"]
        self.assertIsNone(information_center["x"])
        self.assertIsNone(information_center["y"])
        self.assertEqual(information_center["width"], 1120)
        self.assertEqual(information_center["height"], 720)
        self.assertEqual(information_center["page_id"], "family_status")
        self.assertTrue(
            any("config schema 3 已升級" in warning for warning in warnings)
        )

    def test_normalize_config_state_resets_invalid_information_center_block(self):
        normalized, warnings = normalize_config_state(
            {
                "schema_version": CONFIG_SCHEMA_VERSION,
                "dashboard": {
                    "information_center": "bad",
                },
            }
        )

        self.assertEqual(
            normalized["dashboard"]["information_center"]["page_id"],
            "family_status",
        )
        self.assertTrue(
            any(
                "dashboard.information_center 區塊不是物件"
                in warning
                for warning in warnings
            )
        )

    def test_schema_four_config_receives_disabled_social_status_default(self):
        normalized, warnings = normalize_config_state(
            {
                "schema_version": 4,
                "dashboard": {
                    "world_mode": "golden_legend",
                },
            }
        )

        self.assertFalse(
            normalized["dashboard"]["social_status_enabled"]
        )
        self.assertTrue(
            any("config schema 4 已升級" in warning for warning in warnings)
        )

    def test_schema_five_config_receives_life_rhythm_defaults(self):
        normalized, warnings = normalize_config_state(
            {
                "schema_version": 5,
                "dashboard": {"world_mode": "sandbox"},
            }
        )

        self.assertEqual(normalized["dashboard"]["race_frequency"], "normal")
        self.assertEqual(normalized["dashboard"]["mood_climate"], "cheerful")
        self.assertTrue(
            any("config schema 5 已升級" in warning for warning in warnings)
        )

    def test_invalid_life_rhythm_options_fall_back_to_defaults(self):
        normalized, _warnings = normalize_config_state(
            {
                "schema_version": CONFIG_SCHEMA_VERSION,
                "dashboard": {
                    "race_frequency": "always",
                    "mood_climate": "chaos",
                },
            }
        )

        self.assertEqual(normalized["dashboard"]["race_frequency"], "normal")
        self.assertEqual(normalized["dashboard"]["mood_climate"], "cheerful")


if __name__ == "__main__":
    unittest.main()
