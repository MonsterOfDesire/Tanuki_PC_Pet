import unittest

from tanuki_core.achievement_state import (
    ACHIEVEMENT_PERSISTENCE_SCHEMA_VERSION,
    MAX_PROCESSED_ACHIEVEMENT_EVENTS,
    AchievementState,
    apply_achievement_persistence_state,
    capture_achievement_persistence_state,
)


class AchievementStateTests(unittest.TestCase):
    def test_round_trip_preserves_isolated_progress_and_event_ids(self):
        original = AchievementState()
        sandbox = original.progress_for("sandbox", "race.first")
        sandbox.count = 4
        sandbox.observed_keys.update({'"practice_100m"', '"practice_400m"'})
        sandbox.updated_at = 42.0
        sandbox.unlock(45.0)
        golden = original.progress_for(
            "golden_legend",
            "work.rudolf_first",
        )
        golden.count = 1
        golden.unlock(60.0)
        original.mark_event_processed("sandbox", "race-4")
        original.mark_event_processed("golden_legend", "work-1")

        payload = capture_achievement_persistence_state(original)
        restored = AchievementState()
        applied = apply_achievement_persistence_state(payload, restored)

        self.assertTrue(applied)
        self.assertEqual(
            payload["achievement_schema_version"],
            ACHIEVEMENT_PERSISTENCE_SCHEMA_VERSION,
        )
        self.assertEqual(
            restored.progress_for("sandbox", "race.first").count,
            4,
        )
        self.assertEqual(
            restored.progress_for("sandbox", "race.first").unlocked_at,
            45.0,
        )
        self.assertEqual(
            restored.progress_for(
                "golden_legend",
                "work.rudolf_first",
            ).unlocked_at,
            60.0,
        )
        self.assertTrue(restored.has_processed_event("sandbox", "race-4"))
        self.assertFalse(
            restored.has_processed_event("golden_legend", "race-4")
        )

    def test_invalid_payload_does_not_apply(self):
        state = AchievementState()
        state.progress_for("sandbox", "keep").count = 2

        applied = apply_achievement_persistence_state([], state)

        self.assertFalse(applied)
        self.assertEqual(state.progress_for("sandbox", "keep").count, 2)

    def test_reset_achievement_clears_only_unlocked_target_progress(self):
        state = AchievementState()
        target = state.progress_for("sandbox", "race.first")
        target.count = 4
        target.observed_keys.add("practice_400m")
        target.unlock(45.0)
        untouched = state.progress_for("sandbox", "chorus.first")
        untouched.unlock(60.0)
        state.mark_event_processed("sandbox", "race-event-1")

        self.assertTrue(
            state.reset_achievement("sandbox", "race.first")
        )

        reset = state.progress_for("sandbox", "race.first")
        self.assertEqual(reset.count, 0)
        self.assertEqual(reset.observed_keys, set())
        self.assertFalse(reset.unlocked)
        self.assertTrue(state.is_unlocked("sandbox", "chorus.first"))
        self.assertTrue(
            state.has_processed_event("sandbox", "race-event-1")
        )
        self.assertFalse(
            state.reset_achievement("sandbox", "race.first")
        )

    def test_restore_sanitizes_negative_and_malformed_values(self):
        state = AchievementState()

        apply_achievement_persistence_state(
            {
                "progress_by_world_mode": {
                    "sandbox": {
                        "race.first": {
                            "count": -8,
                            "observed_keys": "not-a-list",
                            "observed_event_names": ["activity.race.completed", ""],
                            "unlocked_at": "invalid",
                            "completion_count": -3,
                            "updated_at": -9,
                        }
                    }
                },
                "processed_event_ids": {
                    "sandbox": ["event-1", "", None],
                },
            },
            state,
        )

        progress = state.progress_for("sandbox", "race.first")
        self.assertEqual(progress.count, 0)
        self.assertEqual(progress.observed_keys, set())
        self.assertEqual(
            progress.observed_event_names,
            {"activity.race.completed"},
        )
        self.assertIsNone(progress.unlocked_at)
        self.assertEqual(progress.completion_count, 0)
        self.assertEqual(progress.updated_at, 0.0)
        self.assertEqual(state.processed_event_ids["sandbox"], {"event-1"})

    def test_processed_event_ids_keep_only_the_most_recent_bound(self):
        state = AchievementState()

        for index in range(MAX_PROCESSED_ACHIEVEMENT_EVENTS + 3):
            state.mark_event_processed("sandbox", f"event-{index}")

        self.assertEqual(
            len(state.processed_event_ids["sandbox"]),
            MAX_PROCESSED_ACHIEVEMENT_EVENTS,
        )
        self.assertFalse(state.has_processed_event("sandbox", "event-0"))
        self.assertTrue(
            state.has_processed_event(
                "sandbox",
                f"event-{MAX_PROCESSED_ACHIEVEMENT_EVENTS + 2}",
            )
        )


if __name__ == "__main__":
    unittest.main()
