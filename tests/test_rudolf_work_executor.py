import unittest

from tanuki_core.activity_coordinator import ActivityCoordinator
from tanuki_core.activity_runtime_adapter import ActivityRuntimeAdapter
from tanuki_core.activity_state import PetActivityState
from tanuki_core.household_event_rules import (
    HouseholdEventScheduleState,
    RUDOLF_WORK_INTERVAL_SECONDS,
)
from tanuki_core.household_state import HouseholdState
from tanuki_core.rudolf_work_executor import RudolfWorkExecutor
from tanuki_core.rudolf_work_rules import (
    RUDOLF_WORK_REST_PHASE,
    RUDOLF_WORK_WORKING_PHASE,
)
from tanuki_core.rudolf_work_settlement import (
    RudolfWorkSettlementAdapter,
)
from tanuki_core.sleep_rules import build_sleep_activity_spec


class FakeAssetManager:
    def __init__(self):
        self.calls = []

    def get_contextual_result_for_purposes(
        self,
        purposes,
        context=None,
        preferred_moods=None,
        forbidden=None,
        mood_score=None,
        ordered_preferences=False,
    ):
        self.calls.append((context, mood_score))
        if context == "activity_work_stationary":
            return (["work-frame"], "idle", "work", "hurry")
        if context == "activity_work_rest":
            return (["rest-frame"], "idle", "rest", "exhausted")
        return None


class FakeRudolf:
    def __init__(self, *, mood_score=60.0):
        self.name = "Symboli Rudolf"
        self.mood_score = mood_score
        self.asset_manager = FakeAssetManager()
        self.activity_state = PetActivityState()
        self.dragging = False
        self.is_angry_locked = False
        self.is_recovering = False
        self.care_mode = "none"
        self.care_partner = None
        self.social_mode = "none"
        self.intent_kind = "none"
        self.flight_mode = "none"
        self.perched_window_hwnd = 0
        self.vy = 0.0
        self.offer_scene_kind = "none"
        self.held_item_kind = ""
        self.user_visible = True
        self.visible = True
        self.state = "idle"
        self.state_timer = 0
        self.fall_origin_y = None
        self.apply_calls = []

    def isVisible(self):
        return self.visible

    def is_under_care(self, now):
        return False

    def is_offer_locked(self, now):
        return False

    def apply_animation_result(self, purpose, result):
        self.apply_calls.append((purpose, result))
        return True

    def refresh_movement_state(self):
        return None


class RecordingCallback:
    def __init__(self, *, fail_count=0):
        self.fail_count = fail_count
        self.events = []

    def __call__(self, event):
        self.events.append(event)
        if len(self.events) <= self.fail_count:
            return None
        return object()


def build_executor():
    coordinator = ActivityCoordinator(
        activity_id_factory=lambda: "work-1",
        event_id_factory=lambda: "event-1",
    )
    return (
        RudolfWorkExecutor(
            coordinator=coordinator,
            runtime_adapter=ActivityRuntimeAdapter(),
            settlement_adapter=RudolfWorkSettlementAdapter(),
        ),
        coordinator,
    )


class RudolfWorkExecutorTests(unittest.TestCase):
    def setUp(self):
        self.executor, self.coordinator = build_executor()
        self.pet = FakeRudolf()
        self.household = HouseholdState(
            living_fund=800,
            household_pressure=10.0,
        )
        self.schedule = HouseholdEventScheduleState(
            next_teio_drink_at=999.0,
            next_rudolf_work_at=10.0,
            next_rudolf_collectible_at=999.0,
        )
        self.recorder = RecordingCallback()

    def update(self, now, **overrides):
        arguments = {
            "now": now,
            "world_mode": "golden_legend",
            "household": self.household,
            "event_schedule": self.schedule,
            "rudolf_pet": self.pet,
            "record_household_event": self.recorder,
        }
        arguments.update(overrides)
        return self.executor.update(**arguments)

    def test_due_schedule_starts_stationary_work(self):
        result = self.update(10.0)

        self.assertTrue(result.started)
        self.assertEqual(self.pet.activity_state.phase, RUDOLF_WORK_WORKING_PHASE)
        self.assertEqual(
            self.schedule.next_rudolf_work_at,
            10.0 + RUDOLF_WORK_INTERVAL_SECONDS,
        )
        self.assertEqual(
            self.pet.asset_manager.calls[-1],
            ("activity_work_stationary", 60.0),
        )

    def test_severe_mood_prevents_start_and_consumes_attempt(self):
        self.pet.mood_score = 10.0

        result = self.update(10.0)

        self.assertFalse(result.handled)
        self.assertEqual(result.reason, "severe_mood")
        self.assertFalse(self.pet.activity_state.active)
        self.assertEqual(
            self.schedule.next_rudolf_work_at,
            10.0 + RUDOLF_WORK_INTERVAL_SECONDS,
        )

    def test_work_completion_commits_once_then_enters_ignore_band_rest(self):
        self.update(10.0)

        result = self.update(18.0)

        self.assertTrue(result.result_committed)
        self.assertTrue(result.phase_changed)
        self.assertEqual(len(self.recorder.events), 1)
        self.assertEqual(
            self.recorder.events[0].event_type,
            "rudolf_work_completed",
        )
        self.assertEqual(
            self.pet.activity_state.phase,
            RUDOLF_WORK_REST_PHASE,
        )
        self.assertEqual(
            self.pet.asset_manager.calls[-1],
            ("activity_work_rest", None),
        )
        self.assertEqual(self.pet.mood_score, 54.0)

        finished = self.update(21.0)

        self.assertTrue(finished.finished)
        self.assertFalse(self.pet.activity_state.active)
        self.assertEqual(len(self.recorder.events), 1)
        self.assertEqual(self.pet.mood_score, 54.0)

    def test_large_time_jump_commits_and_finishes_exactly_once(self):
        self.update(10.0)

        result = self.update(30.0)

        self.assertTrue(result.finished)
        self.assertTrue(result.result_committed)
        self.assertFalse(self.pet.activity_state.active)
        self.assertEqual(len(self.recorder.events), 1)
        self.assertEqual(self.recorder.events[0].occurred_at, 18.0)

    def test_hidden_participant_interrupts_before_income(self):
        self.update(10.0)
        self.pet.visible = False

        result = self.update(12.0)

        self.assertTrue(result.interrupted)
        self.assertFalse(self.pet.activity_state.active)
        self.assertEqual(self.recorder.events, [])

    def test_non_golden_mode_does_not_consume_schedule(self):
        result = self.update(10.0, world_mode="desktop")

        self.assertFalse(result.handled)
        self.assertEqual(result.reason, "world_mode_disabled")
        self.assertEqual(self.schedule.next_rudolf_work_at, 10.0)

    def test_other_activity_is_not_mistaken_for_rudolf_work(self):
        snapshot = ActivityRuntimeAdapter().build_participant_snapshot(
            self.pet,
            role="sleeper",
            now=1.0,
        )
        started = self.coordinator.start(
            build_sleep_activity_spec(30.0),
            owner_name=self.pet.name,
            participant_snapshots=(snapshot,),
            now=1.0,
            source="test",
        )

        result = self.update(10.0)
        interrupted = self.executor.interrupt_active(
            now=10.1,
            reason="test",
            rudolf_pet=self.pet,
        )

        self.assertTrue(started.started)
        self.assertEqual(result.reason, "other_activity_active")
        self.assertEqual(self.schedule.next_rudolf_work_at, 10.0)
        self.assertEqual(interrupted.reason, "unsupported_activity")
        self.assertIsNotNone(
            self.coordinator.get_activity(started.activity_id)
        )

    def test_sandbox_preview_runs_both_phases_without_any_settlement(self):
        initial_fund = self.household.living_fund
        initial_pressure = self.household.household_pressure
        initial_mood = self.pet.mood_score

        started = self.executor.start_preview(
            now=10.0,
            world_mode="sandbox",
            rudolf_pet=self.pet,
        )

        self.assertTrue(started.started)
        self.assertTrue(self.executor.is_preview_active())
        self.assertEqual(
            self.pet.activity_state.phase,
            RUDOLF_WORK_WORKING_PHASE,
        )
        self.assertEqual(self.schedule.next_rudolf_work_at, 10.0)

        resting = self.update(18.0, world_mode="sandbox")

        self.assertTrue(resting.phase_changed)
        self.assertFalse(resting.result_committed)
        self.assertEqual(
            self.pet.activity_state.phase,
            RUDOLF_WORK_REST_PHASE,
        )
        self.assertEqual(
            self.pet.asset_manager.calls[-1],
            ("activity_work_rest", None),
        )

        finished = self.update(21.0, world_mode="sandbox")

        self.assertTrue(finished.finished)
        self.assertFalse(self.executor.is_preview_active())
        self.assertFalse(self.pet.activity_state.active)
        self.assertEqual(self.recorder.events, [])
        self.assertEqual(self.household.living_fund, initial_fund)
        self.assertEqual(
            self.household.household_pressure,
            initial_pressure,
        )
        self.assertEqual(self.pet.mood_score, initial_mood)
        self.assertEqual(
            self.executor._pending_settlement_events,
            {},
        )

    def test_sandbox_preview_keeps_severe_and_activity_busy_gates(self):
        self.pet.mood_score = 10.0

        severe = self.executor.start_preview(
            now=10.0,
            world_mode="sandbox",
            rudolf_pet=self.pet,
        )

        self.assertFalse(severe.started)
        self.assertEqual(severe.reason, "severe_mood")

        self.pet.mood_score = 60.0
        first = self.executor.start_preview(
            now=11.0,
            world_mode="sandbox",
            rudolf_pet=self.pet,
        )
        duplicate = self.executor.start_preview(
            now=11.1,
            world_mode="sandbox",
            rudolf_pet=self.pet,
        )

        self.assertTrue(first.started)
        self.assertFalse(duplicate.started)
        self.assertEqual(duplicate.reason, "participant_owned")
        self.assertEqual(
            len(self.coordinator.get_active_activities()),
            1,
        )

    def test_sandbox_preview_interrupts_when_world_mode_changes(self):
        self.executor.start_preview(
            now=10.0,
            world_mode="sandbox",
            rudolf_pet=self.pet,
        )

        result = self.update(
            11.0,
            world_mode="golden_legend",
        )

        self.assertTrue(result.interrupted)
        self.assertEqual(result.reason, "world_mode_changed")
        self.assertFalse(self.pet.activity_state.active)
        self.assertEqual(self.recorder.events, [])

    def test_failed_settlement_retries_before_phase_transition(self):
        self.recorder = RecordingCallback(fail_count=1)
        self.update(10.0)

        pending = self.update(18.0)

        self.assertEqual(pending.reason, "settlement_pending")
        self.assertEqual(
            self.pet.activity_state.phase,
            RUDOLF_WORK_WORKING_PHASE,
        )
        self.assertEqual(len(self.recorder.events), 1)
        self.assertEqual(self.pet.mood_score, 54.0)

        retried = self.update(18.5)

        self.assertTrue(retried.phase_changed)
        self.assertEqual(
            self.pet.activity_state.phase,
            RUDOLF_WORK_REST_PHASE,
        )
        self.assertEqual(len(self.recorder.events), 2)
        self.assertEqual(self.pet.mood_score, 54.0)

    def test_committed_settlement_survives_external_interruption(self):
        self.recorder = RecordingCallback(fail_count=1)
        self.update(10.0)
        self.update(18.0)

        interrupted = self.executor.interrupt_active(
            now=18.1,
            reason="world_mode_changed",
            rudolf_pet=self.pet,
        )

        self.assertTrue(interrupted.interrupted)
        self.assertFalse(self.pet.activity_state.active)

        retried = self.update(18.2, world_mode="desktop")

        self.assertEqual(retried.reason, "world_mode_disabled")
        self.assertEqual(len(self.recorder.events), 2)
        self.assertEqual(
            len(self.executor._pending_settlement_events),
            0,
        )


if __name__ == "__main__":
    unittest.main()
