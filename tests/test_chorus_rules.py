import unittest

from tanuki_core.chorus_rules import (
    CHORUS_APPROACH_PHASE,
    CHORUS_FINISH_PHASE,
    CHORUS_OBSERVE_PHASE,
    CHORUS_NOTICE_MAX_DISTANCE,
    CHORUS_BASE_DURATION_SECONDS,
    CHORUS_MAX_DURATION_SECONDS,
    ChorusEligibilitySnapshot,
    build_chorus_activity_spec,
    decide_chorus_reaction,
    evaluate_chorus_eligibility,
    extend_chorus_end_time,
    get_chorus_schedule_policy,
    reserve_chorus_approach_time,
)


class ChorusRulesTests(unittest.TestCase):
    def test_notice_distance_supports_wide_desktop_layouts(self):
        self.assertEqual(CHORUS_NOTICE_MAX_DISTANCE, 1500.0)

    def test_starter_duration_is_one_minute_with_three_minute_cap(self):
        self.assertEqual(CHORUS_BASE_DURATION_SECONDS, 60.0)
        self.assertEqual(CHORUS_MAX_DURATION_SECONDS, 180.0)

    def test_frequency_scales_all_schedule_intervals(self):
        frequent = get_chorus_schedule_policy("frequent")
        normal = get_chorus_schedule_policy("normal")
        occasional = get_chorus_schedule_policy("occasional")

        self.assertEqual(frequent.initial_delay_min_seconds, 60.0)
        self.assertEqual(frequent.retry_max_seconds, 30.0)
        self.assertEqual(normal.cooldown_min_seconds, 180.0)
        self.assertEqual(occasional.initial_delay_max_seconds, 480.0)
        self.assertEqual(occasional.cooldown_max_seconds, 720.0)

    def test_transformed_teio_can_start_but_base_rudolf_cannot(self):
        transformed_teio = evaluate_chorus_eligibility(
            ChorusEligibilitySnapshot(
                character_name="Tokai Teio",
                form_key="transformed",
                world_mode="sandbox",
                mood_score=60.0,
            ),
            autonomous_start=True,
        )
        base_rudolf = evaluate_chorus_eligibility(
            ChorusEligibilitySnapshot(
                character_name="Symboli Rudolf",
                form_key="base",
                world_mode="sandbox",
                mood_score=60.0,
            ),
            autonomous_start=True,
        )

        self.assertTrue(transformed_teio.allowed)
        self.assertFalse(base_rudolf.allowed)
        self.assertEqual(base_rudolf.reason, "form_cannot_initiate")

    def test_severe_mood_never_reacts(self):
        decision = decide_chorus_reaction(
            mood_score=10.0,
            roll=0.0,
            can_perform=True,
            can_observe=True,
        )

        self.assertEqual(decision.reaction, "ignore")

    def test_missing_observe_capability_is_not_selected(self):
        decision = decide_chorus_reaction(
            mood_score=60.0,
            roll=0.7,
            can_perform=True,
            can_observe=False,
        )

        self.assertNotEqual(decision.reaction, "audience")

    def test_each_arrived_performer_extends_with_hard_cap(self):
        end = extend_chorus_end_time(
            started_at=10.0,
            current_ends_at=22.0,
            now=18.0,
            performer_count=3,
        )
        capped = extend_chorus_end_time(
            started_at=10.0,
            current_ends_at=end,
            now=40.0,
            performer_count=9,
        )

        self.assertEqual(end, 130.0)
        self.assertEqual(capped, 190.0)

    def test_late_candidate_reserves_approach_and_observation_time(self):
        reserved = reserve_chorus_approach_time(
            started_at=10.0,
            current_ends_at=70.0,
            now=50.0,
        )
        capped = reserve_chorus_approach_time(
            started_at=10.0,
            current_ends_at=reserved,
            now=170.0,
        )

        self.assertEqual(reserved, 140.0)
        self.assertEqual(capped, 190.0)

    def test_audience_activity_uses_approach_observe_finish(self):
        spec = build_chorus_activity_spec(
            "audience",
            begins_with_approach=True,
        )

        self.assertEqual(
            tuple(phase.name for phase in spec.phases),
            (
                CHORUS_APPROACH_PHASE,
                CHORUS_OBSERVE_PHASE,
                CHORUS_FINISH_PHASE,
            ),
        )


if __name__ == "__main__":
    unittest.main()
