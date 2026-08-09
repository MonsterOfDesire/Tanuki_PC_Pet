import unittest

from tanuki_core.achievement_eligibility import (
    ACHIEVEMENT_SOURCE_AUTONOMOUS,
    ACHIEVEMENT_SOURCE_SETTINGS_PREVIEW,
    AchievementEligibilityGuard,
    INELIGIBLE_TEST_SOURCE,
    INELIGIBLE_TIME_SCALE_AT_START,
    INELIGIBLE_TIME_SCALE_CHANGED,
    INELIGIBLE_WORLD_MODE_CHANGED,
    classify_achievement_source_kind,
)


class AchievementEligibilityTests(unittest.TestCase):
    def test_full_one_x_session_is_eligible(self):
        guard = AchievementEligibilityGuard()
        guard.begin_session(
            session_id="race-1",
            world_mode="sandbox",
            source_kind=ACHIEVEMENT_SOURCE_AUTONOMOUS,
            time_scale=1.0,
            started_at=10.0,
        )

        decision = guard.finish_session(
            session_id="race-1",
            event_id="race-1:completed",
            world_mode="sandbox",
            time_scale=1.0,
            ended_at=20.0,
        )

        self.assertTrue(decision.eligible)
        self.assertEqual(decision.reason, "")
        self.assertEqual(decision.started_at, 10.0)

    def test_starting_at_fast_speed_is_permanently_ineligible(self):
        guard = AchievementEligibilityGuard()
        token = guard.begin_session(
            session_id="race-fast",
            world_mode="sandbox",
            source_kind=ACHIEVEMENT_SOURCE_AUTONOMOUS,
            time_scale=8.0,
            started_at=10.0,
        )

        decision = guard.finish_session(
            session_id="race-fast",
            event_id="race-fast:completed",
            world_mode="sandbox",
            time_scale=1.0,
            ended_at=12.0,
        )

        self.assertFalse(token.eligible)
        self.assertFalse(decision.eligible)
        self.assertEqual(decision.reason, INELIGIBLE_TIME_SCALE_AT_START)

    def test_leaving_one_x_invalidates_all_active_sessions(self):
        guard = AchievementEligibilityGuard()
        for session_id in ("race-1", "chorus-1"):
            guard.begin_session(
                session_id=session_id,
                world_mode="sandbox",
                source_kind=ACHIEVEMENT_SOURCE_AUTONOMOUS,
                time_scale=1.0,
                started_at=1.0,
            )

        invalidated = guard.observe_time_scale(2.0)
        guard.observe_time_scale(1.0)
        decision = guard.finish_session(
            session_id="race-1",
            event_id="race-1:completed",
            world_mode="sandbox",
            time_scale=1.0,
            ended_at=5.0,
        )

        self.assertEqual(set(invalidated), {"race-1", "chorus-1"})
        self.assertFalse(decision.eligible)
        self.assertEqual(decision.reason, INELIGIBLE_TIME_SCALE_CHANGED)

    def test_world_mode_change_invalidates_session(self):
        guard = AchievementEligibilityGuard()
        guard.begin_session(
            session_id="sleep-1",
            world_mode="sandbox",
            source_kind=ACHIEVEMENT_SOURCE_AUTONOMOUS,
            time_scale=1.0,
            started_at=3.0,
        )

        invalidated = guard.observe_world_mode("golden_legend")
        decision = guard.finish_session(
            session_id="sleep-1",
            event_id="sleep-1:completed",
            world_mode="golden_legend",
            time_scale=1.0,
            ended_at=8.0,
        )

        self.assertEqual(invalidated, ("sleep-1",))
        self.assertFalse(decision.eligible)
        self.assertEqual(decision.reason, INELIGIBLE_WORLD_MODE_CHANGED)

    def test_settings_preview_instant_event_is_rejected(self):
        guard = AchievementEligibilityGuard()

        decision = guard.qualify_instantaneous(
            event_id="preview-1",
            world_mode="sandbox",
            source_kind=ACHIEVEMENT_SOURCE_SETTINGS_PREVIEW,
            time_scale=1.0,
            occurred_at=4.0,
        )

        self.assertFalse(decision.eligible)
        self.assertEqual(decision.reason, INELIGIBLE_TEST_SOURCE)

    def test_current_runtime_sources_are_classified_without_ui_text(self):
        self.assertEqual(
            classify_achievement_source_kind(
                "race_schedule",
                "autonomous",
            ),
            ACHIEVEMENT_SOURCE_AUTONOMOUS,
        )
        self.assertEqual(
            classify_achievement_source_kind(
                "settings_preview",
                "sandbox_preview",
            ),
            ACHIEVEMENT_SOURCE_SETTINGS_PREVIEW,
        )


if __name__ == "__main__":
    unittest.main()
