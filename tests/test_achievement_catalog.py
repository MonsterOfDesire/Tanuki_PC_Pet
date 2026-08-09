import unittest
from pathlib import Path

from tanuki_core.achievement_catalog import (
    load_achievement_catalog,
    load_achievement_catalog_payload,
)


CATALOG_PATH = (
    Path(__file__).resolve().parents[1]
    / "UI"
    / "trophies"
    / "achievement_catalog_draft.json"
)


class AchievementCatalogTests(unittest.TestCase):
    def test_project_catalog_has_isolated_mode_definitions(self):
        catalog = load_achievement_catalog(CATALOG_PATH)

        self.assertEqual(len(catalog.definitions), 26)
        self.assertEqual(
            len(catalog.definitions_for_mode("sandbox")),
            24,
        )
        self.assertEqual(
            len(catalog.definitions_for_mode("golden_legend")),
            2,
        )
        ui_root = CATALOG_PATH.parents[1]
        self.assertTrue(
            all(
                (ui_root / definition.trophy.image).is_file()
                for definition in catalog.definitions
            )
        )
        self.assertTrue(
            all(
                definition.world_mode in {"sandbox", "golden_legend"}
                for definition in catalog.definitions
            )
        )

    def test_definition_cannot_be_shared_between_world_modes(self):
        with self.assertRaisesRegex(ValueError, "exactly one world mode"):
            load_achievement_catalog_payload(
                _catalog_payload(
                    [_definition(world_modes=["sandbox", "golden_legend"])]
                )
            )

    def test_meta_achievement_cannot_cross_world_modes(self):
        dependency = _definition(
            achievement_id="sandbox.first",
            world_modes=["sandbox"],
        )
        meta = _definition(
            achievement_id="golden.meta",
            world_modes=["golden_legend"],
            rule={
                "type": "all_of_achievements",
                "achievement_ids": ["sandbox.first"],
            },
        )

        with self.assertRaisesRegex(ValueError, "crosses world modes"):
            load_achievement_catalog_payload(_catalog_payload([dependency, meta]))


def _catalog_payload(definitions):
    return {"schema_version": 1, "achievements": definitions}


def _definition(
    *,
    achievement_id="sandbox.first",
    world_modes=None,
    rule=None,
):
    return {
        "achievement_id": achievement_id,
        "title_zh_tw": "測試",
        "description_zh_tw": "測試成就",
        "tier": "G3",
        "trophy": {
            "type": "race",
            "id": "3001",
            "image": "trophies/race/3001.png",
        },
        "world_modes": list(world_modes or ["sandbox"]),
        "rule": dict(rule or {
            "type": "event_count",
            "event_name": "activity.test.completed",
            "target": 1,
        }),
        "implementation_status": "ready_existing_event",
    }


if __name__ == "__main__":
    unittest.main()
