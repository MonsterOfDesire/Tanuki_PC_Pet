import unittest
from pathlib import Path

from tanuki_core.achievement_catalog import load_achievement_catalog
from tanuki_core.achievement_eligibility import (
    ACHIEVEMENT_SOURCE_AUTONOMOUS,
)
from tanuki_core.achievement_tracker import (
    AchievementGameplayEvent,
    AchievementTracker,
)


CATALOG_PATH = (
    Path(__file__).resolve().parents[1]
    / "UI"
    / "trophies"
    / "achievement_catalog_draft.json"
)


class AchievementTrackerTests(unittest.TestCase):
    def setUp(self):
        self.tracker = AchievementTracker(
            load_achievement_catalog(CATALOG_PATH)
        )

    def test_first_race_unlocks_once_and_duplicate_event_is_rejected(self):
        event = _event(
            "race-1",
            "activity.race.completed",
            payload={
                "race_course_key": "practice_100m",
                "direction_key": "clockwise_left",
            },
        )

        first = self.tracker.consume_event(event)
        duplicate = self.tracker.consume_event(event)

        self.assertTrue(first.accepted)
        self.assertIn(
            "race.first_natural_finish",
            first.unlocked_achievement_ids,
        )
        self.assertFalse(duplicate.accepted)
        self.assertEqual(duplicate.reason, "duplicate_event")
        self.assertEqual(
            self.tracker.state.progress_for(
                "sandbox",
                "race.first_natural_finish",
            ).completion_count,
            1,
        )

    def test_world_mode_catalogs_do_not_share_progress(self):
        result = self.tracker.consume_event(
            _event("work-sandbox", "activity.work.completed")
        )

        self.assertTrue(result.accepted)
        self.assertFalse(
            self.tracker.state.is_unlocked(
                "golden_legend",
                "work.rudolf_first_complete",
            )
        )
        golden_result = self.tracker.consume_event(
            _event(
                "work-golden",
                "activity.work.completed",
                world_mode="golden_legend",
            )
        )
        self.assertIn(
            "work.rudolf_first_complete",
            golden_result.unlocked_achievement_ids,
        )

    def test_ineligible_event_is_not_processed_or_counted(self):
        result = self.tracker.consume_event(
            _event(
                "race-fast",
                "activity.race.completed",
                eligible=False,
                ineligible_reason="time_scale_changed_during_session",
            )
        )

        self.assertFalse(result.accepted)
        self.assertEqual(
            result.reason,
            "time_scale_changed_during_session",
        )
        self.assertFalse(
            self.tracker.state.has_processed_event(
                "sandbox",
                "race-fast",
            )
        )

    def test_distinct_course_and_direction_rules_unlock(self):
        courses = (
            "practice_100m",
            "practice_200m",
            "practice_400m",
            "practice_800m",
        )
        unlocked = set()
        for index, course in enumerate(courses):
            result = self.tracker.consume_event(
                _event(
                    f"race-{index}",
                    "activity.race.completed",
                    payload={
                        "race_course_key": course,
                        "direction_key": (
                            "clockwise_left"
                            if index % 2 == 0
                            else "counterclockwise_right"
                        ),
                    },
                )
            )
            unlocked.update(result.unlocked_achievement_ids)

        self.assertIn("race.all_course_lengths", unlocked)
        self.assertIn("race.both_directions", unlocked)

    def test_winner_form_is_derived_from_existing_race_payload(self):
        winners = (
            ("Tokai Teio", "base"),
            ("Sirius Symboli", "base"),
            ("Symboli Rudolf", "base"),
            ("Symboli Rudolf", "transformed"),
        )
        unlocked = set()
        for index, (winner_name, winner_form) in enumerate(winners):
            opponent_name = (
                "Sirius Symboli"
                if winner_name != "Sirius Symboli"
                else "Tokai Teio"
            )
            result = self.tracker.consume_event(
                _event(
                    f"winner-{index}",
                    "activity.race.completed",
                    payload={
                        "winner_name": winner_name,
                        "challenger_name": winner_name,
                        "challenger_form": winner_form,
                        "opponent_name": opponent_name,
                        "opponent_form": "base",
                        "race_course_key": "practice_100m",
                        "direction_key": "clockwise_left",
                    },
                )
            )
            unlocked.update(result.unlocked_achievement_ids)

        self.assertIn("race.every_competitor_form_wins", unlocked)

    def test_participant_role_and_single_event_threshold_rules_unlock(self):
        participants = tuple(
            {"name": name, "role": "perform"}
            for name in (
                "Air Groove",
                "Sirius Symboli",
                "Symboli Rudolf",
                "Tokai Teio",
                "Tsurumaru Tsuyoshi",
            )
        )

        result = self.tracker.consume_event(
            _event(
                "chorus-five",
                "activity.chorus.completed",
                payload={"performer_count": 5},
                participants=participants,
            )
        )

        self.assertIn(
            "chorus.every_character_performed",
            result.unlocked_achievement_ids,
        )
        self.assertIn(
            "chorus.five_performers_same_session",
            result.unlocked_achievement_ids,
        )

    def test_all_of_event_names_unlocks_variety_sampler(self):
        event_names = (
            "activity.race.completed",
            "activity.chorus.completed",
            "activity.sleep.completed",
            "interaction.care.completed",
            "activity.transformation.completed",
        )
        unlocked = set()
        for index, event_name in enumerate(event_names):
            result = self.tracker.consume_event(
                _event(
                    f"variety-{index}",
                    event_name,
                    payload={
                        "source_kind": ACHIEVEMENT_SOURCE_AUTONOMOUS,
                        "character_name": "Tokai Teio",
                        "target_form": "transformed",
                    },
                )
            )
            unlocked.update(result.unlocked_achievement_ids)

        self.assertIn("activity.variety_sampler", unlocked)

    def test_state_snapshot_unlocks_simultaneous_sleep(self):
        result = self.tracker.consume_state_snapshot(
            snapshot_id="sleep-snapshot-1",
            world_mode="sandbox",
            source_kind=ACHIEVEMENT_SOURCE_AUTONOMOUS,
            occurred_at=90.0,
            state_payload={
                "naturally_sleeping_character_names": [
                    "Air Groove",
                    "Sirius Symboli",
                    "Symboli Rudolf",
                    "Tokai Teio",
                    "Tsurumaru Tsuyoshi",
                ]
            },
        )

        self.assertIn(
            "sleep.five_simultaneous",
            result.unlocked_achievement_ids,
        )


def _event(
    event_id,
    event_name,
    *,
    world_mode="sandbox",
    payload=None,
    participants=(),
    eligible=True,
    ineligible_reason="",
):
    return AchievementGameplayEvent(
        event_id=event_id,
        event_name=event_name,
        world_mode=world_mode,
        source_kind=ACHIEVEMENT_SOURCE_AUTONOMOUS,
        occurred_at=100.0,
        started_at=90.0,
        payload=dict(payload or {}),
        participants=tuple(participants),
        eligible=eligible,
        ineligible_reason=ineligible_reason,
    )


if __name__ == "__main__":
    unittest.main()
