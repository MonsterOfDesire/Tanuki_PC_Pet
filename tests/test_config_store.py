import json
import tempfile
import unittest
from pathlib import Path

from tanuki_core.config_store import ConfigStore


class FakeDashboard:
    world_mode = "golden_legend"
    care_feature_enabled = True
    teio_dur_idx = 3
    tsuyoshi_dur_idx = 2
    time_scale_idx = 0
    display_scale_idx = 0
    debug_enabled = False

    def capture_config_state(self):
        return type(
            "DashboardState",
            (),
            {
                "care_feature_enabled": self.care_feature_enabled,
                "teio_dur_idx": self.teio_dur_idx,
                "tsuyoshi_dur_idx": self.tsuyoshi_dur_idx,
                "time_scale_idx": self.time_scale_idx,
                "display_scale_idx": self.display_scale_idx,
                "debug_enabled": self.debug_enabled,
                "world_mode": self.world_mode,
            },
        )()

    def capture_household_config_state(self):
        return {
            "living_fund": 1200,
            "household_pressure": 8.0,
        }


class FakePet:
    def __init__(self):
        self._x = 120
        self._y = 340
        self.user_visible = True

    def x(self):
        return self._x

    def y(self):
        return self._y

    def isVisible(self):
        return self.user_visible


class ConfigStoreTests(unittest.TestCase):
    def test_save_now_writes_payload(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.json"
            store = ConfigStore(str(config_path), clamp_pet_position=lambda pet, x, y: (x, y))
            store.dashboard = FakeDashboard()
            store.pets_dict = {"Tokai Teio": {"pet": FakePet()}}

            store.save_now(force=True)

            payload = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertIn("dashboard", payload)
            self.assertIn("pets", payload)
            self.assertIn("household", payload)
            self.assertEqual(payload["dashboard"]["world_mode"], "golden_legend")
            self.assertEqual(payload["household"]["living_fund"], 1200)

    def test_load_collects_migration_warnings_for_legacy_payload(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "care_feature_enabled": False,
                        "time_scale_idx": 2,
                        "pets": {"Tokai Teio": {"x": 10, "y": 20, "user_visible": True}},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            store = ConfigStore(str(config_path), clamp_pet_position=lambda pet, x, y: (x, y))

            self.assertFalse(store.loaded_state["dashboard"]["care_feature_enabled"])
            self.assertEqual(store.loaded_state["dashboard"]["time_scale_idx"], 2)
            self.assertTrue(any("root-level dashboard" in warning for warning in store.validation_warnings))


if __name__ == "__main__":
    unittest.main()
