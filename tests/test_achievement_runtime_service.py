import unittest
from pathlib import Path

from tanuki_core.achievement_catalog import load_achievement_catalog
from tanuki_core.achievement_eligibility import (
    AchievementEligibilityGuard,
)
from tanuki_core.achievement_runtime_service import (
    AchievementRuntimeService,
)
from tanuki_core.achievement_state import AchievementState
from tanuki_core.activity_event_contract import (
    ACTIVITY_EVENT_CHORUS_COMPLETED,
    ACTIVITY_EVENT_RACE_COMPLETED,
    ACTIVITY_EVENT_SLEEP_GROUP_JOINED,
    ACTIVITY_EVENT_WORK_COMPLETED,
    build_activity_event_metadata,
)


CATALOG_PATH = (
    Path(__file__).resolve().parents[1]
    / "UI"
    / "trophies"
    / "achievement_catalog_draft.json"
)


class AchievementRuntimeServiceTests(unittest.TestCase):
    def setUp(self):
        self.speed = 1.0
        self.state = AchievementState()
        self.guard = AchievementEligibilityGuard()
        self.changed_results = []
        self.service = AchievementRuntimeService(
            catalog=load_achievement_catalog(CATALOG_PATH),
            state=self.state,
            eligibility_guard=self.guard,
            time_scale_provider=lambda: self.speed,
            state_changed_callback=self.changed_results.append,
        )

    def test_race_session_consumes_canonical_metadata_and_unlocks(self):
        started = self.service.begin_activity_session(
            activity_id="race-1",
            world_mode="sandbox",
            source="autonomous",
            execution_mode="autonomous",
            started_at=10.0,
        )

        result = self.service.consume_activity_metadata(
            _metadata(
                event_name=ACTIVITY_EVENT_RACE_COMPLETED,
                event_id="race-1:race_completed",
                activity_id="race-1",
                activity_kind="race",
                world_mode="sandbox",
                started_at=10.0,
                ended_at=20.0,
                participants=(
                    ("Tokai Teio", "challenger"),
                    ("Symboli Rudolf", "opponent"),
                ),
                extra={
                    "winner_name": "Tokai Teio",
                    "challenger_name": "Tokai Teio",
                    "challenger_form": "base",
                    "opponent_name": "Symboli Rudolf",
                    "opponent_form": "base",
                    "race_course_key": "practice_100m",
                    "direction_key": "clockwise_left",
                },
            )
        )

        self.assertTrue(started)
        self.assertTrue(result.accepted)
        self.assertIn(
            "race.first_natural_finish",
            result.unlocked_achievement_ids,
        )
        self.assertEqual(self.changed_results, [result])
        self.assertNotIn("race-1", self.guard.active_session_ids)

    def test_speed_change_cannot_be_recovered_before_completion(self):
        self.service.begin_activity_session(
            activity_id="chorus-fast",
            world_mode="sandbox",
            source="autonomous",
            execution_mode="autonomous",
            started_at=5.0,
        )
        self.speed = 8.0
        self.guard.observe_time_scale(self.speed)
        self.speed = 1.0

        result = self.service.consume_activity_metadata(
            _metadata(
                event_name=ACTIVITY_EVENT_CHORUS_COMPLETED,
                event_id="chorus-fast:completed",
                activity_id="chorus-fast",
                activity_kind="chorus",
                world_mode="sandbox",
                started_at=5.0,
                ended_at=15.0,
                participants=(("Tokai Teio", "perform"),),
                extra={"performer_count": 1},
            )
        )

        self.assertFalse(result.accepted)
        self.assertEqual(
            result.reason,
            "time_scale_changed_during_session",
        )
        self.assertFalse(
            self.state.is_unlocked(
                "sandbox",
                "chorus.first_natural_finish",
            )
        )
        self.assertEqual(self.changed_results, [])

    def test_missing_start_token_is_rejected(self):
        result = self.service.consume_activity_metadata(
            _metadata(
                event_name=ACTIVITY_EVENT_RACE_COMPLETED,
                event_id="orphan:completed",
                activity_id="orphan",
                activity_kind="race",
                world_mode="sandbox",
                started_at=1.0,
                ended_at=2.0,
            )
        )

        self.assertFalse(result.accepted)
        self.assertEqual(result.reason, "missing_eligibility_session")

    def test_golden_work_only_updates_golden_catalog(self):
        self.service.begin_activity_session(
            activity_id="work-1",
            world_mode="golden_legend",
            source="household_schedule",
            execution_mode="normal",
            started_at=30.0,
        )

        result = self.service.consume_activity_metadata(
            _metadata(
                event_name=ACTIVITY_EVENT_WORK_COMPLETED,
                event_id="work-1:completed",
                activity_id="work-1",
                activity_kind="rudolf_work",
                world_mode="golden_legend",
                started_at=30.0,
                ended_at=90.0,
                participants=(("Symboli Rudolf", "worker"),),
            )
        )

        self.assertIn(
            "work.rudolf_first_complete",
            result.unlocked_achievement_ids,
        )
        self.assertFalse(
            self.state.is_unlocked(
                "sandbox",
                "race.first_natural_finish",
            )
        )

    def test_cancelled_session_cannot_be_consumed_later(self):
        self.service.begin_activity_session(
            activity_id="race-cancelled",
            world_mode="sandbox",
            source="autonomous",
            execution_mode="autonomous",
            started_at=10.0,
        )

        cancelled = self.service.cancel_activity_session(
            "race-cancelled",
            reason="user_drag",
        )
        result = self.service.consume_activity_metadata(
            _metadata(
                event_name=ACTIVITY_EVENT_RACE_COMPLETED,
                event_id="race-cancelled:completed",
                activity_id="race-cancelled",
                activity_kind="race",
                world_mode="sandbox",
                started_at=10.0,
                ended_at=12.0,
            )
        )

        self.assertTrue(cancelled)
        self.assertFalse(result.accepted)
        self.assertEqual(result.reason, "missing_eligibility_session")

    def test_instantaneous_group_join_unlocks_at_one_x(self):
        result = self.service.consume_instantaneous_activity_metadata(
            _metadata(
                event_name=ACTIVITY_EVENT_SLEEP_GROUP_JOINED,
                event_id="sleep-join-1:joined",
                activity_id="sleep-join-1",
                activity_kind="sleep_join",
                world_mode="sandbox",
                started_at=10.0,
                ended_at=10.0,
                participants=(
                    ("Tokai Teio", "joiner"),
                    ("Sirius Symboli", "anchor"),
                ),
            )
        )

        self.assertTrue(result.accepted)
        self.assertIn(
            "sleep.first_group_join",
            result.unlocked_achievement_ids,
        )

    def test_five_sleepers_snapshot_unlocks_simultaneous_achievement(self):
        names = [
            "Air Groove",
            "Sirius Symboli",
            "Symboli Rudolf",
            "Tokai Teio",
            "Tsurumaru Tsuyoshi",
        ]

        result = self.service.consume_state_snapshot(
            snapshot_id="sleep-snapshot-live-1",
            world_mode="sandbox",
            source="sleep_schedule",
            execution_mode="autonomous",
            occurred_at=50.0,
            state_payload={
                "naturally_sleeping_character_names": names,
            },
        )

        self.assertTrue(result.accepted)
        self.assertIn(
            "sleep.five_simultaneous",
            result.unlocked_achievement_ids,
        )


def _metadata(
    *,
    event_name,
    event_id,
    activity_id,
    activity_kind,
    world_mode,
    started_at,
    ended_at,
    participants=(),
    extra=None,
):
    return build_activity_event_metadata(
        event_name=event_name,
        event_id=event_id,
        activity_id=activity_id,
        activity_kind=activity_kind,
        participants=participants,
        source="autonomous",
        execution_mode="autonomous",
        world_mode=world_mode,
        phase="finish",
        started_at=started_at,
        ended_at=ended_at,
        outcome="completed",
        extra=extra,
    )


if __name__ == "__main__":
    unittest.main()
