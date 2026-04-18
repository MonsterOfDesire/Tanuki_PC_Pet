import unittest

from tanuki_core.config_rules import (
    CONFIG_SCHEMA_VERSION,
    migrate_config_state,
    normalize_config_state,
)


class ConfigRuleTests(unittest.TestCase):
    def test_normalize_config_state_upgrades_schema_and_preserves_known_fields(self):
        normalized, warnings = normalize_config_state(
            {
                "schema_version": 1,
                "dashboard": {
                    "care_feature_enabled": False,
                    "debug_enabled": True,
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
        self.assertFalse(normalized["dashboard"]["care_feature_enabled"])
        self.assertTrue(normalized["dashboard"]["debug_enabled"])
        self.assertEqual(normalized["pets"]["Tokai Teio"]["x"], 10)
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
        self.assertEqual(normalized["pets"], {})
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
        self.assertFalse(migrated["dashboard"]["care_feature_enabled"])
        self.assertEqual(migrated["dashboard"]["time_scale_idx"], 2)
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
                "dashboard": {"debug_enabled": True},
                "pets": {},
            }
        )

        self.assertEqual(migrated["schema_version"], CONFIG_SCHEMA_VERSION)
        self.assertEqual(original_version, CONFIG_SCHEMA_VERSION)
        self.assertTrue(any("高於目前支援版本" in warning for warning in warnings))


if __name__ == "__main__":
    unittest.main()
