import unittest

from tanuki_core.activity_coordinator import ActivityCoordinator
from tanuki_core.activity_state import (
    ActivityParticipant,
    ActivityParticipantSnapshot,
    ActivityPhaseSpec,
    ActivitySpec,
    COLLISION_POLICY_BLOCK,
    INTERRUPT_POLICY_FORCE_ONLY,
)


class SequentialIdFactory:
    def __init__(self, prefix):
        self.prefix = prefix
        self.index = 0

    def __call__(self):
        self.index += 1
        return f"{self.prefix}-{self.index}"


def build_spec():
    return ActivitySpec(
        kind="rudolf_work",
        phases=(
            ActivityPhaseSpec("prepare", 1.0),
            ActivityPhaseSpec(
                "working",
                3.0,
                collision_policy=COLLISION_POLICY_BLOCK,
                interrupt_policy=INTERRUPT_POLICY_FORCE_ONLY,
            ),
            ActivityPhaseSpec("rest", 2.0),
        ),
        blocked_operations=frozenset(
            {
                "offer",
                "care_give",
                "care_receive",
                "social_start",
                "observe_start",
                "windowing",
                "drag",
                "random",
            }
        ),
    )


def snapshot(name="Symboli Rudolf", role="worker", **kwargs):
    return ActivityParticipantSnapshot(
        ActivityParticipant(name, role),
        **kwargs,
    )


class ActivityCoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.coordinator = ActivityCoordinator(
            activity_id_factory=SequentialIdFactory("activity"),
            event_id_factory=SequentialIdFactory("event"),
        )

    def start_work(self, now=10.0):
        return self.coordinator.start(
            build_spec(),
            owner_name="Symboli Rudolf",
            participant_snapshots=(snapshot(),),
            now=now,
            source="household_schedule",
            metadata={"profile_key": "rudolf_work_v1"},
        )

    def test_start_claims_participant_and_builds_projection_and_event(self):
        result = self.start_work()

        self.assertTrue(result.started)
        self.assertEqual(result.activity_id, "activity-1")
        self.assertEqual(result.events[0].event_name, "activity.started")
        self.assertEqual(result.events[0].event_id, "event-1")
        self.assertEqual(result.projections[0].participant_name, "Symboli Rudolf")
        state = result.projections[0].state
        self.assertTrue(state.active)
        self.assertEqual(state.activity_kind, "rudolf_work")
        self.assertEqual(state.phase, "prepare")
        self.assertEqual(state.phase_ends_at, 11.0)
        self.assertEqual(state.deadline_at, 16.0)
        self.assertEqual(state.participant_role, "worker")

        payload = result.events[0].to_payload()
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["activity_id"], "activity-1")
        self.assertEqual(
            payload["participants"],
            [{"name": "Symboli Rudolf", "role": "worker"}],
        )
        self.assertEqual(
            payload["metadata"]["profile_key"],
            "rudolf_work_v1",
        )

    def test_start_rejects_internal_or_snapshot_participant_ownership(self):
        first = self.start_work()
        internal_conflict = self.coordinator.start(
            build_spec(),
            owner_name="Symboli Rudolf",
            participant_snapshots=(snapshot(),),
            now=20.0,
        )
        snapshot_conflict = self.coordinator.start(
            build_spec(),
            owner_name="Air Groove",
            participant_snapshots=(
                snapshot(
                    "Air Groove",
                    active_activity_id="external-activity",
                ),
            ),
            now=20.0,
        )

        self.assertTrue(first.started)
        self.assertFalse(internal_conflict.started)
        self.assertEqual(internal_conflict.reason, "participant_owned")
        self.assertFalse(snapshot_conflict.started)
        self.assertEqual(snapshot_conflict.reason, "participant_owned")

    def test_non_overlapping_activities_can_run_concurrently(self):
        first = self.start_work()
        second = self.coordinator.start(
            build_spec(),
            owner_name="Air Groove",
            participant_snapshots=(snapshot("Air Groove"),),
            now=10.0,
        )

        self.assertTrue(first.started)
        self.assertTrue(second.started)
        self.assertEqual(len(self.coordinator.get_active_activities()), 2)

    def test_update_catches_up_multiple_phases_and_releases_once(self):
        started = self.start_work(now=10.0)

        result = self.coordinator.update(
            started.activity_id,
            now=16.0,
        )
        repeated = self.coordinator.update(
            started.activity_id,
            now=30.0,
        )

        self.assertTrue(result.handled)
        self.assertTrue(result.finished)
        self.assertEqual(
            [event.event_name for event in result.events],
            [
                "activity.phase_changed",
                "activity.phase_changed",
                "activity.completed",
            ],
        )
        self.assertEqual(
            [event.occurred_at for event in result.events],
            [11.0, 14.0, 16.0],
        )
        self.assertEqual(
            result.released_participant_names,
            ("Symboli Rudolf",),
        )
        self.assertIsNone(
            self.coordinator.get_activity_for_participant(
                "Symboli Rudolf"
            )
        )
        self.assertFalse(repeated.handled)
        self.assertEqual(repeated.reason, "activity_not_found")

    def test_update_returns_phase_projection_and_busy_policy(self):
        started = self.start_work(now=10.0)

        result = self.coordinator.update(
            started.activity_id,
            now=11.0,
        )
        busy = self.coordinator.is_busy_for(
            "Symboli Rudolf",
            "offer",
        )
        unrelated = self.coordinator.is_busy_for(
            "Symboli Rudolf",
            "unknown_operation",
        )

        self.assertTrue(result.handled)
        self.assertFalse(result.finished)
        self.assertEqual(result.projections[0].state.phase, "working")
        self.assertEqual(
            result.projections[0].state.collision_policy,
            COLLISION_POLICY_BLOCK,
        )
        self.assertTrue(busy.busy)
        self.assertEqual(busy.activity_id, started.activity_id)
        self.assertFalse(unrelated.busy)

    def test_explicit_forward_transition_restarts_target_phase_at_now(self):
        started = self.start_work(now=10.0)

        result = self.coordinator.transition_to_phase(
            started.activity_id,
            phase_name="rest",
            now=10.5,
            reason="early_finish",
        )

        self.assertTrue(result.handled)
        self.assertEqual(result.projections[0].state.phase, "rest")
        self.assertEqual(result.projections[0].state.phase_started_at, 10.5)
        self.assertEqual(result.projections[0].state.phase_ends_at, 12.5)
        self.assertEqual(result.projections[0].state.deadline_at, 12.5)
        self.assertEqual(result.events[0].reason, "early_finish")
        self.assertEqual(
            result.events[0].metadata["previous_phase"],
            "prepare",
        )

    def test_result_can_be_committed_only_once(self):
        started = self.start_work()

        first = self.coordinator.commit_result(
            started.activity_id,
            now=14.0,
            result={"living_fund_delta": 80},
        )
        repeated = self.coordinator.commit_result(
            started.activity_id,
            now=14.5,
            result={"living_fund_delta": 800},
        )

        self.assertTrue(first.handled)
        self.assertTrue(first.result_committed)
        self.assertEqual(
            first.events[0].event_name,
            "activity.result_committed",
        )
        self.assertEqual(
            first.events[0].result,
            {"living_fund_delta": 80},
        )
        self.assertFalse(repeated.handled)
        self.assertEqual(repeated.reason, "result_already_committed")
        self.assertEqual(repeated.events, ())

    def test_cancel_releases_owner_and_emits_terminal_event_once(self):
        started = self.start_work()

        cancelled = self.coordinator.cancel(
            started.activity_id,
            now=12.0,
            reason="manual",
        )
        repeated = self.coordinator.cancel(
            started.activity_id,
            now=13.0,
            reason="manual",
        )

        self.assertTrue(cancelled.handled)
        self.assertTrue(cancelled.finished)
        self.assertEqual(
            cancelled.events[0].event_name,
            "activity.cancelled",
        )
        self.assertEqual(cancelled.events[0].reason, "manual")
        self.assertFalse(repeated.handled)

    def test_force_only_phase_rejects_regular_interrupt_but_allows_shutdown(self):
        started = self.start_work(now=10.0)
        self.coordinator.update(started.activity_id, now=11.0)

        rejected = self.coordinator.interrupt(
            started.activity_id,
            now=12.0,
            reason="pet_hidden",
        )
        forced = self.coordinator.interrupt(
            started.activity_id,
            now=12.0,
            reason="shutdown",
            force=True,
        )

        self.assertFalse(rejected.handled)
        self.assertEqual(rejected.reason, "interrupt_requires_force")
        self.assertTrue(forced.handled)
        self.assertEqual(
            forced.events[0].event_name,
            "activity.interrupted",
        )
        self.assertEqual(forced.events[0].reason, "shutdown")


if __name__ == "__main__":
    unittest.main()
