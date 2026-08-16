import unittest
from pathlib import Path

from tanuki_core.achievement_catalog import load_achievement_catalog
from tanuki_core.achievement_presenter import (
    build_achievement_cabinet_snapshot,
    build_achievement_unlock_notification,
)
from tanuki_core.achievement_state import AchievementState


CATALOG_PATH = (
    Path(__file__).resolve().parents[1]
    / "UI"
    / "trophies"
    / "achievement_catalog_draft.json"
)


class AchievementPresenterTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load_achievement_catalog(CATALOG_PATH)
        self.state = AchievementState()

    def test_snapshot_separates_modes_and_strips_locked_information(self):
        snapshot = build_achievement_cabinet_snapshot(
            self.catalog,
            self.state,
        )

        sandbox = snapshot.mode_snapshot("sandbox")
        golden = snapshot.mode_snapshot("golden_legend")
        locked = snapshot.card_snapshot("race.first_natural_finish")

        self.assertEqual((sandbox.total_count, golden.total_count), (25, 2))
        self.assertEqual((sandbox.unlocked_count, golden.unlocked_count), (0, 0))
        self.assertFalse(locked.unlocked)
        self.assertEqual(locked.title, "")
        self.assertEqual(locked.acquisition_method, "")
        self.assertEqual(locked.unlocked_at_text, "")
        self.assertEqual(locked.accessible_name, "未取得的 G3 獎盃")

    def test_unlocked_card_and_mode_summary_show_only_completed_details(self):
        self.state.progress_for(
            "sandbox",
            "race.first_natural_finish",
        ).unlock(1_700_000_000.0)

        snapshot = build_achievement_cabinet_snapshot(
            self.catalog,
            self.state,
        )
        card = snapshot.card_snapshot("race.first_natural_finish")
        sandbox = snapshot.mode_snapshot("sandbox")

        self.assertTrue(card.unlocked)
        self.assertEqual(card.title, "初次奔馳")
        self.assertIn("第一場", card.acquisition_method)
        self.assertTrue(card.unlocked_at_text)
        self.assertEqual(sandbox.unlocked_count, 1)
        self.assertIn("最近：初次奔馳", sandbox.summary_text)

    def test_unlock_notification_combines_multiple_unlocks(self):
        achievement_ids = (
            "race.first_natural_finish",
            "chorus.first_natural_finish",
        )
        for achievement_id in achievement_ids:
            self.state.progress_for("sandbox", achievement_id).unlock(
                1_700_000_000.0
            )
        snapshot = build_achievement_cabinet_snapshot(
            self.catalog,
            self.state,
        )

        notification = build_achievement_unlock_notification(
            snapshot,
            achievement_ids,
        )

        self.assertEqual(notification.achievement_ids, achievement_ids)
        self.assertEqual(notification.heading, "一次獲得 2 項成就")
        self.assertIn("初次奔馳", notification.message)
        self.assertIn("初次合奏", notification.message)


if __name__ == "__main__":
    unittest.main()
