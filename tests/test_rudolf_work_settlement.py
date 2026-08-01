import unittest

from tanuki_core.activity_state import (
    ActivityDomainEvent,
    ActivityParticipant,
)
from tanuki_core.household_event_rules import HouseholdEventScheduleState
from tanuki_core.household_runtime_coordinator import HouseholdRuntimeCoordinator
from tanuki_core.household_state import HouseholdEventLog, HouseholdState
from tanuki_core.rudolf_work_rules import build_rudolf_work_result
from tanuki_core.rudolf_work_settlement import (
    RudolfWorkSettlementAdapter,
)


def build_result_event(**overrides):
    values = {
        "event_name": "activity.result_committed",
        "event_id": "event-1",
        "activity_id": "activity-1",
        "activity_kind": "rudolf_work",
        "owner_name": "Symboli Rudolf",
        "participants": (
            ActivityParticipant("Symboli Rudolf", "worker"),
        ),
        "phase": "working",
        "occurred_at": 18.0,
        "started_at": 10.0,
        "source": "household_schedule",
        "result": build_rudolf_work_result(),
        "metadata": {"profile_key": "rudolf_work_v1"},
    }
    values.update(overrides)
    return ActivityDomainEvent(**values)


class RudolfWorkSettlementAdapterTests(unittest.TestCase):
    def test_valid_result_builds_canonical_household_event(self):
        adapter = RudolfWorkSettlementAdapter()

        decision = adapter.resolve(build_result_event())

        self.assertTrue(decision.ready)
        event = decision.household_event
        self.assertEqual(event.event_type, "rudolf_work_completed")
        self.assertEqual(event.channel, "economy")
        self.assertEqual(event.actor_name, "Symboli Rudolf")
        self.assertEqual(event.living_fund_delta, 80)
        self.assertEqual(event.household_pressure_delta, -6.0)
        self.assertEqual(event.mood_delta, -6.0)
        self.assertEqual(event.tags, ("activity", "work", "completed"))
        self.assertEqual(event.metadata["activity_id"], "activity-1")
        self.assertEqual(event.metadata["activity_elapsed_seconds"], 8.0)
        self.assertEqual(
            event.metadata["participant_roles"],
            {"Symboli Rudolf": "worker"},
        )

    def test_apply_records_and_settles_each_activity_only_once(self):
        adapter = RudolfWorkSettlementAdapter()
        calls = []

        def record_event(event):
            calls.append(event)
            return object()

        first = adapter.apply(
            build_result_event(),
            record_event=record_event,
            apply_mood_delta=lambda mood_delta: True,
        )
        repeated = adapter.apply(
            build_result_event(event_id="event-2"),
            record_event=record_event,
            apply_mood_delta=lambda mood_delta: True,
        )

        self.assertTrue(first.applied)
        self.assertFalse(repeated.applied)
        self.assertEqual(repeated.reason, "activity_already_settled")
        self.assertEqual(len(calls), 1)
        self.assertEqual(
            adapter.settled_activity_ids,
            frozenset({"activity-1"}),
        )

    def test_rejected_or_failed_record_does_not_mark_activity_settled(self):
        adapter = RudolfWorkSettlementAdapter()
        invalid = adapter.apply(
            build_result_event(event_name="activity.completed"),
            record_event=lambda event: object(),
            apply_mood_delta=lambda mood_delta: True,
        )
        mood_calls = []
        failed = adapter.apply(
            build_result_event(),
            record_event=lambda event: None,
            apply_mood_delta=lambda mood_delta: (
                mood_calls.append(mood_delta) or True
            ),
        )

        self.assertFalse(invalid.applied)
        self.assertEqual(invalid.reason, "unsupported_event")
        self.assertFalse(failed.applied)
        self.assertEqual(failed.reason, "record_event_failed")
        self.assertEqual(adapter.settled_activity_ids, frozenset())

        retried = adapter.apply(
            build_result_event(event_id="event-2"),
            record_event=lambda event: object(),
            apply_mood_delta=lambda mood_delta: (
                mood_calls.append(mood_delta) or True
            ),
        )

        self.assertTrue(retried.applied)
        self.assertEqual(mood_calls, [-6.0])

    def test_adapter_rejects_wrong_activity_or_tampered_deltas(self):
        adapter = RudolfWorkSettlementAdapter()
        wrong_activity = adapter.resolve(
            build_result_event(activity_kind="sleep")
        )
        tampered_result = build_rudolf_work_result()
        tampered_result["living_fund_delta"] = 800
        tampered = adapter.resolve(
            build_result_event(result=tampered_result)
        )

        self.assertEqual(
            wrong_activity.reason,
            "unsupported_activity",
        )
        self.assertEqual(
            tampered.reason,
            "unexpected_result_delta",
        )

    def test_existing_household_coordinator_applies_settlement_once(self):
        household = HouseholdState(
            living_fund=700,
            household_pressure=30.0,
        )
        household_coordinator = HouseholdRuntimeCoordinator(
            household=household,
            event_log=HouseholdEventLog(),
            event_schedule=HouseholdEventScheduleState(),
        )
        adapter = RudolfWorkSettlementAdapter()

        def record_event(event):
            return household_coordinator.record_resolved_event(event)

        first = adapter.apply(
            build_result_event(),
            record_event=record_event,
            apply_mood_delta=lambda mood_delta: True,
        )
        repeated = adapter.apply(
            build_result_event(event_id="event-2"),
            record_event=record_event,
            apply_mood_delta=lambda mood_delta: True,
        )

        self.assertTrue(first.applied)
        self.assertFalse(repeated.applied)
        self.assertEqual(household.living_fund, 780)
        self.assertEqual(household.household_pressure, 24.0)
        self.assertEqual(len(household_coordinator.event_log.entries), 1)
        self.assertEqual(
            household_coordinator.event_log.entries[0].event_type,
            "rudolf_work_completed",
        )
        self.assertEqual(
            household_coordinator.event_log.entries[0].mood_delta,
            -6.0,
        )


if __name__ == "__main__":
    unittest.main()
