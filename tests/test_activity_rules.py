import unittest

from tanuki_core.activity_rules import (
    decide_activity_busy,
    decide_activity_interrupt,
    evaluate_activity_start,
    resolve_activity_policy,
)
from tanuki_core.activity_state import (
    ActiveActivity,
    ActivityParticipant,
    ActivityParticipantSnapshot,
    ActivityPhaseSpec,
    ActivitySpec,
    COLLISION_POLICY_BLOCK,
    COLLISION_POLICY_IGNORE,
    INTERRUPT_POLICY_ALLOW,
    INTERRUPT_POLICY_FORCE_ONLY,
)


def build_spec():
    return ActivitySpec(
        kind="rudolf_work",
        phases=(
            ActivityPhaseSpec("prepare", 1.0),
            ActivityPhaseSpec(
                "working",
                4.0,
                blocked_operations=frozenset({"offer", "drag"}),
                collision_policy=COLLISION_POLICY_BLOCK,
                interrupt_policy=INTERRUPT_POLICY_FORCE_ONLY,
            ),
        ),
        blocked_operations=frozenset({"offer"}),
        collision_policy=COLLISION_POLICY_IGNORE,
        interrupt_policy=INTERRUPT_POLICY_ALLOW,
    )


def build_active_activity(phase_index=0):
    spec = build_spec()
    participant = ActivityParticipant("Symboli Rudolf", "worker")
    return ActiveActivity(
        activity_id="activity-1",
        spec=spec,
        owner_name=participant.name,
        participants=(participant,),
        source="test",
        started_at=10.0,
        phase_index=phase_index,
        phase_started_at=11.0,
        phase_ends_at=15.0,
        deadline_at=15.0,
    )


class ActivityRuleTests(unittest.TestCase):
    def test_start_requires_visible_available_capable_participants(self):
        spec = build_spec()
        participant = ActivityParticipant("Symboli Rudolf", "worker")

        allowed = evaluate_activity_start(
            spec,
            participant.name,
            (ActivityParticipantSnapshot(participant),),
        )
        busy = evaluate_activity_start(
            spec,
            participant.name,
            (
                ActivityParticipantSnapshot(
                    participant,
                    busy_reasons=("offer", "care"),
                ),
            ),
        )
        unavailable = evaluate_activity_start(
            spec,
            participant.name,
            (
                ActivityParticipantSnapshot(
                    participant,
                    capability_ready=False,
                    capability_reason="missing_work_context",
                ),
            ),
        )

        self.assertTrue(allowed.allowed)
        self.assertFalse(busy.allowed)
        self.assertEqual(busy.reason, "participant_busy:offer")
        self.assertEqual(busy.participant_name, participant.name)
        self.assertEqual(
            unavailable.reason,
            "capability_unavailable:missing_work_context",
        )

    def test_start_rejects_duplicate_or_missing_owner(self):
        spec = build_spec()
        participant = ActivityParticipant("Symboli Rudolf", "worker")
        snapshot = ActivityParticipantSnapshot(participant)

        duplicate = evaluate_activity_start(
            spec,
            participant.name,
            (snapshot, snapshot),
        )
        missing_owner = evaluate_activity_start(
            spec,
            "Air Groove",
            (snapshot,),
        )

        self.assertEqual(duplicate.reason, "duplicate_participant")
        self.assertEqual(missing_owner.reason, "owner_not_participant")

    def test_phase_policy_overrides_spec_defaults(self):
        spec = build_spec()

        prepare = resolve_activity_policy(spec, 0)
        working = resolve_activity_policy(spec, 1)

        self.assertEqual(prepare.blocked_operations, frozenset({"offer"}))
        self.assertEqual(prepare.collision_policy, COLLISION_POLICY_IGNORE)
        self.assertEqual(prepare.interrupt_policy, INTERRUPT_POLICY_ALLOW)
        self.assertEqual(
            working.blocked_operations,
            frozenset({"offer", "drag"}),
        )
        self.assertEqual(working.collision_policy, COLLISION_POLICY_BLOCK)
        self.assertEqual(
            working.interrupt_policy,
            INTERRUPT_POLICY_FORCE_ONLY,
        )

    def test_busy_reason_includes_activity_kind_and_phase(self):
        activity = build_active_activity(phase_index=1)

        offer = decide_activity_busy(activity, "offer")
        care = decide_activity_busy(activity, "care_give")
        another_activity = decide_activity_busy(
            activity,
            "activity_start",
        )

        self.assertTrue(offer.busy)
        self.assertEqual(
            offer.reason,
            "activity:rudolf_work:working",
        )
        self.assertFalse(care.busy)
        self.assertTrue(another_activity.busy)
        self.assertIn("owns_participant", another_activity.reason)

    def test_force_only_interrupt_policy_allows_forced_cleanup(self):
        activity = build_active_activity(phase_index=1)

        regular = decide_activity_interrupt(activity, force=False)
        forced = decide_activity_interrupt(activity, force=True)

        self.assertFalse(regular.allowed)
        self.assertEqual(regular.reason, "interrupt_requires_force")
        self.assertTrue(forced.allowed)


if __name__ == "__main__":
    unittest.main()
