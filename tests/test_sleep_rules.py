import unittest

from tanuki_core.sleep_rules import (
    SLEEP_ACTIVITY_KIND,
    SLEEP_BLOCKED_OPERATIONS,
    SLEEP_SETTLING_PHASE,
    SLEEP_WAKING_PHASE,
    SLEEPING_PHASE,
    SleepEligibilitySnapshot,
    SleepJoinCandidateSnapshot,
    SleepJoinInfluenceSnapshot,
    build_sleep_activity_spec,
    evaluate_sleep_eligibility,
    evaluate_sleep_join_candidate,
    evaluate_sleep_join_influence,
)


class SleepRuleTests(unittest.TestCase):
    def test_activity_spec_has_three_interruptible_phases(self):
        spec = build_sleep_activity_spec(30.0)

        self.assertEqual(spec.kind, SLEEP_ACTIVITY_KIND)
        self.assertEqual(
            tuple(phase.name for phase in spec.phases),
            (
                SLEEP_SETTLING_PHASE,
                SLEEPING_PHASE,
                SLEEP_WAKING_PHASE,
            ),
        )
        self.assertEqual(spec.phases[1].duration_seconds, 30.0)
        self.assertEqual(spec.blocked_operations, SLEEP_BLOCKED_OPERATIONS)
        self.assertEqual(spec.collision_policy, "ignore")
        self.assertEqual(spec.interrupt_policy, "allow")

    def test_sleep_requires_due_schedule_and_available_capacity(self):
        early = evaluate_sleep_eligibility(
            SleepEligibilitySnapshot("Air Groove", 9.0, 10.0)
        )
        full = evaluate_sleep_eligibility(
            SleepEligibilitySnapshot(
                "Air Groove",
                10.0,
                10.0,
                active_sleep_count=1,
                max_concurrent_sleepers=1,
            )
        )
        allowed = evaluate_sleep_eligibility(
            SleepEligibilitySnapshot("Air Groove", 10.0, 10.0)
        )

        self.assertEqual(early.reason, "schedule_not_due")
        self.assertEqual(full.reason, "sleep_capacity_reached")
        self.assertTrue(allowed.allowed)

    def test_non_positive_sleep_duration_is_rejected(self):
        with self.assertRaises(ValueError):
            build_sleep_activity_spec(0.0)

    def test_sleep_join_requires_sleeping_target_and_distance_but_not_group_limit(self):
        allowed = evaluate_sleep_join_candidate(
            SleepJoinCandidateSnapshot(
                observer_name="Tokai Teio",
                target_name="Symboli Rudolf",
                distance=120.0,
                target_is_sleeping=True,
            )
        )
        too_far = evaluate_sleep_join_candidate(
            SleepJoinCandidateSnapshot(
                observer_name="Tokai Teio",
                target_name="Symboli Rudolf",
                distance=999.0,
                target_is_sleeping=True,
            )
        )
        large_group = evaluate_sleep_join_candidate(
            SleepJoinCandidateSnapshot(
                observer_name="Tokai Teio",
                target_name="Symboli Rudolf",
                distance=120.0,
                target_is_sleeping=True,
                group_size=99,
                reserved_joiners=20,
            )
        )

        self.assertTrue(allowed.allowed)
        self.assertEqual(too_far.reason, "target_too_far")
        self.assertTrue(large_group.allowed)

    def test_sleep_join_influence_is_probabilistic_and_relation_aware(self):
        low_relation = evaluate_sleep_join_influence(
            SleepJoinInfluenceSnapshot(
                awake_seconds=30.0,
                autonomous_schedule_due=False,
                distance=400.0,
            ),
            roll=0.5,
        )
        high_relation = evaluate_sleep_join_influence(
            SleepJoinInfluenceSnapshot(
                awake_seconds=300.0,
                autonomous_schedule_due=True,
                distance=80.0,
                familiarity=60.0,
                attachment=60.0,
            ),
            roll=0.5,
        )

        self.assertFalse(low_relation.should_join)
        self.assertTrue(high_relation.should_join)
        self.assertGreater(
            high_relation.probability,
            low_relation.probability,
        )


if __name__ == "__main__":
    unittest.main()
