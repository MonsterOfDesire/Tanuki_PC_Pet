import unittest

from tanuki_core.activity_state import (
    ActivityParticipant,
    ActivityParticipantSnapshot,
    ActivityPhaseSpec,
    ActivitySpec,
    COLLISION_POLICY_IGNORE,
    INTERRUPT_POLICY_FORCE_ONLY,
    PetActivityState,
)


class ActivityStateTests(unittest.TestCase):
    def test_spec_validates_and_reports_total_duration(self):
        spec = ActivitySpec(
            kind="rudolf_work",
            phases=(
                ActivityPhaseSpec("prepare", 1.5),
                ActivityPhaseSpec("working", 4.0),
            ),
            blocked_operations=frozenset({"offer", "drag", "offer"}),
            collision_policy=COLLISION_POLICY_IGNORE,
            interrupt_policy=INTERRUPT_POLICY_FORCE_ONLY,
        )

        self.assertEqual(spec.duration_seconds, 5.5)
        self.assertEqual(spec.blocked_operations, frozenset({"offer", "drag"}))

    def test_spec_rejects_invalid_phase_contract(self):
        with self.assertRaises(ValueError):
            ActivitySpec(kind="", phases=(ActivityPhaseSpec("work", 1.0),))
        with self.assertRaises(ValueError):
            ActivitySpec(kind="work", phases=())
        with self.assertRaises(ValueError):
            ActivitySpec(
                kind="work",
                phases=(
                    ActivityPhaseSpec("same", 1.0),
                    ActivityPhaseSpec("same", 2.0),
                ),
            )
        with self.assertRaises(ValueError):
            ActivityPhaseSpec("work", 0.0)

    def test_participant_snapshot_normalizes_busy_reasons(self):
        snapshot = ActivityParticipantSnapshot(
            ActivityParticipant("Symboli Rudolf", "worker"),
            busy_reasons=("offer", "", "offer", "care"),
        )

        self.assertEqual(snapshot.busy_reasons, ("offer", "care"))

    def test_pet_activity_state_clear_requires_matching_owner_token(self):
        state = PetActivityState(
            activity_id="activity-2",
            activity_kind="rudolf_work",
            owner_name="Symboli Rudolf",
            participant_role="worker",
            phase="working",
            blocked_operations=frozenset({"offer"}),
            collision_policy=COLLISION_POLICY_IGNORE,
            interrupt_policy=INTERRUPT_POLICY_FORCE_ONLY,
        )

        self.assertFalse(state.clear(expected_activity_id="activity-1"))
        self.assertTrue(state.active)
        self.assertTrue(state.clear(expected_activity_id="activity-2"))
        self.assertFalse(state.active)
        self.assertEqual(state.activity_kind, "none")
        self.assertEqual(state.phase, "none")
        self.assertEqual(state.blocked_operations, frozenset())


if __name__ == "__main__":
    unittest.main()
