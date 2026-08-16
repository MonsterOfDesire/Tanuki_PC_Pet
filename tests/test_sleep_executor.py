import unittest

from tanuki_core.activity_coordinator import ActivityCoordinator
from tanuki_core.activity_runtime_adapter import ActivityRuntimeAdapter
from tanuki_core.activity_state import (
    ActivityPhaseSpec,
    ActivitySpec,
    PetActivityState,
)
from tanuki_core.sleep_executor import SleepExecutor
from tanuki_core.sleep_rules import (
    SLEEP_ACTIVITY_KIND,
    SLEEP_SETTLING_PHASE,
    SLEEP_WAKING_PHASE,
    SLEEPING_PHASE,
)


class FakeAssetManager:
    def __init__(self, missing_context=""):
        self.missing_context = missing_context
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
        if context == self.missing_context:
            return None
        if context in {
            "activity_sleep_observing",
            "activity_sleep_join_approach",
            "activity_sleep_join_settling",
            "activity_sleep_settling",
            "activity_sleeping",
            "activity_sleep_waking",
        }:
            return (
                [f"{context}-frame"],
                "idle",
                "manifest-action",
                "sleep",
            )
        return None


class FakePet:
    def __init__(self, name, *, mood_score=60.0, is_adult=False):
        self.name = name
        self.mood_score = mood_score
        self.is_adult = is_adult
        self.current_mood_tag = ""
        self.distressed = False
        self.asset_manager = FakeAssetManager()
        self.activity_state = PetActivityState()
        self.dragging = False
        self.is_angry_locked = False
        self.is_recovering = False
        self.care_mode = "none"
        self.care_partner = None
        self.social_mode = "none"
        self.intent_kind = "none"
        self.intent_target_name = ""
        self.intent_priority = 0
        self.intent_source = "none"
        self.intent_context = "ambient"
        self.intent_reason = ""
        self.intent_locked_until = 0.0
        self.intent_reconsider_after = 0.0
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
        self.relationship_entries = {}
        self.care_cooldown_end = 0.0
        self.direction = 1
        self._x = 100.0
        self.visual_afterglow_calls = []

    def isVisible(self):
        return self.visible

    def is_under_care(self, now):
        return False

    def is_offer_locked(self, now):
        return False

    def is_distressed(self):
        return self.distressed

    def is_care_feature_enabled(self):
        return True

    def is_care_blocked_by_negative_afterglow(self, now):
        return False

    def apply_animation_result(self, purpose, result):
        self.apply_calls.append((purpose, result))
        return True

    def refresh_movement_state(self):
        return None

    def start_visual_band_afterglow(self, band, *, duration, now):
        self.visual_afterglow_calls.append((band, duration, now))
        return True

    def x(self):
        return self._x

    def width(self):
        return 100

    def distance_to(self, other):
        return abs(self.x() - other.x())

    def move_toward_x(self, target_x, speed_scale=1.0, min_speed=None):
        delta = float(target_x) - self._x
        step = 80.0 * float(speed_scale)
        self._x = (
            float(target_x)
            if abs(delta) <= step
            else self._x + (step if delta > 0 else -step)
        )
        return self._x == float(target_x)


def build_executor():
    sequence = iter(range(1, 100))
    coordinator = ActivityCoordinator(
        activity_id_factory=lambda: f"activity-{next(sequence)}",
        event_id_factory=lambda: f"event-{next(sequence)}",
    )
    executor = SleepExecutor(
        coordinator=coordinator,
        runtime_adapter=ActivityRuntimeAdapter(),
        uniform=lambda minimum, maximum: minimum,
        random_value=lambda: 0.0,
    )
    return executor, coordinator


class SleepExecutorTests(unittest.TestCase):
    def setUp(self):
        self.executor, self.coordinator = build_executor()
        self.pet = FakePet("Air Groove")

    def update(self, now, pets=None, world_mode="sandbox"):
        return self.executor.update(
            now=now,
            pets=(self.pet,) if pets is None else pets,
            world_mode=world_mode,
        )

    def test_schedule_runs_all_three_manifest_context_phases(self):
        self.assertEqual(self.update(0.0), ())

        started = self.update(120.0)[0]

        self.assertTrue(started.started)
        self.assertEqual(self.pet.activity_state.phase, SLEEP_SETTLING_PHASE)
        self.assertEqual(
            self.pet.apply_calls[-1][1][0],
            ["activity_sleep_settling-frame"],
        )

        sleeping = self.update(123.0)[0]
        self.assertTrue(sleeping.phase_changed)
        self.assertEqual(self.pet.activity_state.phase, SLEEPING_PHASE)
        self.assertEqual(
            self.pet.apply_calls[-1][1][0],
            ["activity_sleeping-frame"],
        )

        waking = self.update(168.0)[0]
        self.assertTrue(waking.phase_changed)
        self.assertEqual(self.pet.activity_state.phase, SLEEP_WAKING_PHASE)
        self.assertEqual(
            self.pet.apply_calls[-1][1][0],
            ["activity_sleep_waking-frame"],
        )

        finished = self.update(171.0)[0]
        self.assertTrue(finished.finished)
        self.assertEqual(self.pet.mood_score, 63.0)
        self.assertFalse(self.pet.activity_state.active)
        self.assertEqual(
            self.executor.schedules[self.pet.name].next_proposal_at,
            351.0,
        )

    def test_user_click_enters_waking_phase_instead_of_force_interrupting(self):
        self.update(0.0)
        self.update(120.0)
        self.update(123.0)

        result = self.executor.request_early_wake(
            self.pet,
            now=124.0,
            reason="user_click",
        )

        self.assertTrue(result.handled)
        self.assertTrue(result.phase_changed)
        self.assertEqual(result.reason, "user_click")
        self.assertTrue(self.pet.activity_state.active)
        self.assertEqual(self.pet.activity_state.phase, SLEEP_WAKING_PHASE)
        self.assertEqual(
            self.pet.apply_calls[-1][1][0],
            ["activity_sleep_waking-frame"],
        )

    def test_chorus_noise_wakes_with_low_band_without_changing_mood(self):
        self.update(0.0)
        self.update(120.0)
        self.update(123.0)
        original_mood = self.pet.mood_score

        result = self.executor.request_early_wake(
            self.pet,
            now=124.0,
            reason="chorus_noise",
            waking_band_override="low",
            visual_afterglow_seconds=8.0,
        )

        self.assertTrue(result.phase_changed)
        self.assertEqual(self.pet.mood_score, original_mood)
        self.assertEqual(
            self.pet.asset_manager.calls[-1],
            ("activity_sleep_waking", 30.0),
        )
        self.assertEqual(
            self.pet.visual_afterglow_calls,
            [("low", 8.0, 124.0)],
        )

        finished = self.update(127.0)[0]
        self.assertTrue(finished.finished)
        self.assertEqual(self.pet.mood_score, original_mood)

    def test_sandbox_control_starts_sleep_and_reuses_waking_flow(self):
        started = self.executor.request_sandbox_toggle(
            self.pet,
            now=10.0,
            world_mode="sandbox",
            pets=(self.pet,),
        )

        self.assertTrue(started.started)
        activity = self.coordinator.get_activity(started.activity_id)
        self.assertEqual(activity.source, "sleep_sandbox_control")
        self.assertEqual(
            activity.metadata["sleep_trigger"],
            "sandbox_control",
        )

        waking = self.executor.request_sandbox_toggle(
            self.pet,
            now=11.0,
            world_mode="sandbox",
            pets=(self.pet,),
        )

        self.assertTrue(waking.phase_changed)
        self.assertEqual(self.pet.activity_state.phase, SLEEP_WAKING_PHASE)

    def test_sleep_control_is_sandbox_only(self):
        result = self.executor.request_sandbox_toggle(
            self.pet,
            now=10.0,
            world_mode="golden_legend",
            pets=(self.pet,),
        )

        self.assertFalse(result.handled)
        self.assertEqual(result.reason, "sandbox_required")

    def test_multiple_pets_can_auto_sleep_independently(self):
        second_pet = FakePet("Tokai Teio")
        pets = (self.pet, second_pet)
        self.update(0.0, pets=pets)

        results = self.update(120.0, pets=pets)

        self.assertEqual(sum(result.started for result in results), 2)
        self.assertTrue(self.pet.activity_state.active)
        self.assertTrue(second_pet.activity_state.active)
        self.assertEqual(
            self.coordinator.get_activity_for_participant(
                self.pet.name
            ).metadata["sleep_group_id"],
            "",
        )

    def test_every_visible_pet_can_sleep_without_fixed_global_limit(self):
        pets = tuple(FakePet(f"Pet {index}") for index in range(5))
        self.update(0.0, pets=pets)

        results = self.update(120.0, pets=pets)

        self.assertEqual(sum(result.started for result in results), 5)
        self.assertTrue(all(pet.activity_state.active for pet in pets))

    def test_distressed_child_wakes_shallow_sleeping_sirius_first(self):
        sirius = FakePet("Sirius Symboli", is_adult=True)
        rudolf = FakePet("Symboli Rudolf", is_adult=True)
        air = FakePet("Air Groove", is_adult=True)
        child = FakePet("Tokai Teio")
        pets = (sirius, rudolf, air, child)
        self.update(0.0, pets=pets)
        self.executor.schedules[child.name].next_proposal_at = 1000.0
        self.executor.schedules[child.name].next_social_probe_at = 1000.0
        self.update(120.0, pets=pets)
        self.update(123.0, pets=pets)
        child.distressed = True
        child.mood_score = 10.0
        child.current_mood_tag = "hard-cry"

        results = self.update(124.0, pets=pets)

        wake = next(
            result
            for result in results
            if result.participant_name == sirius.name
            and result.phase_changed
        )
        self.assertEqual(wake.reason, "child_distress")
        self.assertEqual(sirius.activity_state.phase, SLEEP_WAKING_PHASE)
        self.assertEqual(rudolf.activity_state.phase, SLEEPING_PHASE)
        self.assertEqual(air.activity_state.phase, SLEEPING_PHASE)
        self.assertEqual(
            sirius.apply_calls[-1][1][0],
            ["activity_sleep_waking-frame"],
        )
        sirius_activity = self.coordinator.get_activity_for_participant(
            sirius.name
        )
        self.assertEqual(
            sirius_activity.metadata["care_wake_target_name"],
            child.name,
        )

        self.update(127.0, pets=pets)
        self.update(128.0, pets=pets)
        self.assertFalse(sirius.activity_state.active)
        self.assertEqual(rudolf.activity_state.phase, SLEEPING_PHASE)
        self.assertEqual(air.activity_state.phase, SLEEPING_PHASE)
        self.assertLessEqual(sirius.care_cooldown_end, 124.0)

    def test_awake_caregiver_keeps_shallow_sleeper_asleep(self):
        sirius = FakePet("Sirius Symboli", is_adult=True)
        air = FakePet("Air Groove", is_adult=True)
        child = FakePet("Tokai Teio")
        pets = (sirius, air, child)
        self.update(0.0, pets=pets)
        self.executor.schedules[air.name].next_proposal_at = 1000.0
        self.executor.schedules[child.name].next_proposal_at = 1000.0
        self.executor.schedules[child.name].next_social_probe_at = 1000.0
        self.update(120.0, pets=pets)
        self.update(123.0, pets=pets)
        child.distressed = True

        self.update(124.0, pets=pets)

        self.assertEqual(sirius.activity_state.phase, SLEEPING_PHASE)

    def test_nearest_sleeping_adult_wakes_when_sirius_unavailable(self):
        rudolf = FakePet("Symboli Rudolf", is_adult=True)
        air = FakePet("Air Groove", is_adult=True)
        child = FakePet("Tsurumaru Tsuyoshi")
        rudolf._x = 100.0
        air._x = 260.0
        child._x = 300.0
        pets = (rudolf, air, child)
        self.update(0.0, pets=pets)
        self.executor.schedules[child.name].next_proposal_at = 1000.0
        self.executor.schedules[child.name].next_social_probe_at = 1000.0
        self.update(120.0, pets=pets)
        self.update(123.0, pets=pets)
        child.distressed = True

        self.update(124.0, pets=pets)

        self.assertEqual(air.activity_state.phase, SLEEP_WAKING_PHASE)
        self.assertEqual(rudolf.activity_state.phase, SLEEPING_PHASE)

    def test_observer_approaches_and_joins_sleep_group(self):
        observer = FakePet("Tokai Teio")
        observer._x = 350.0
        pets = (self.pet, observer)
        self.update(0.0, pets=pets)
        self.executor.schedules[observer.name].next_proposal_at = 1000.0
        self.executor.schedules[observer.name].next_social_probe_at = 123.0

        self.update(120.0, pets=pets)
        self.update(123.0, pets=pets)

        self.assertIn(observer.name, self.executor.join_attempts)
        self.assertTrue(
            self.executor.update_join_behavior(
                observer,
                pets,
                now=123.0,
                world_mode="sandbox",
            )
        )
        self.assertEqual(
            observer.apply_calls[-1][1][0],
            ["activity_sleep_observing-frame"],
        )

        self.executor.update_join_behavior(
            observer,
            pets,
            now=126.0,
            world_mode="sandbox",
        )
        self.assertEqual(
            observer.apply_calls[-1][1][0],
            ["activity_sleep_join_approach-frame"],
        )
        self.executor.update_join_behavior(
            observer,
            pets,
            now=127.0,
            world_mode="sandbox",
        )

        anchor_activity = self.coordinator.get_activity_for_participant(
            self.pet.name
        )
        joined_activity = self.coordinator.get_activity_for_participant(
            observer.name
        )
        self.assertIsNotNone(joined_activity)
        self.assertEqual(
            joined_activity.metadata["sleep_trigger"],
            "observed_join",
        )
        self.assertEqual(
            anchor_activity.metadata["sleep_group_id"],
            joined_activity.metadata["sleep_group_id"],
        )
        self.assertEqual(
            joined_activity.metadata["sleep_anchor_name"],
            self.pet.name,
        )
        self.assertEqual(
            observer.apply_calls[-1][1][0],
            ["activity_sleep_join_settling-frame"],
        )

        self.update(130.0, pets=pets)
        self.update(168.0, pets=pets)
        self.update(171.0, pets=pets)
        remaining_activity = self.coordinator.get_activity_for_participant(
            observer.name
        )
        self.assertEqual(
            remaining_activity.metadata["sleep_anchor_name"],
            observer.name,
        )
        self.assertEqual(
            remaining_activity.metadata["sleep_group_slot"],
            0,
        )

    def test_activity_ownership_defers_sleep_without_overwriting_activity(self):
        self.update(0.0)
        snapshot = self.executor.runtime_adapter.build_participant_snapshot(
            self.pet,
            role="worker",
            now=1.0,
        )
        external = self.coordinator.start(
            ActivitySpec(
                kind="other_activity",
                phases=(ActivityPhaseSpec("active", 100.0),),
            ),
            owner_name=self.pet.name,
            participant_snapshots=(snapshot,),
            now=1.0,
            source="test",
        )
        self.assertTrue(external.started)

        results = self.update(120.0)

        self.assertEqual(results, ())
        self.assertEqual(
            self.coordinator.get_activity_for_participant(
                self.pet.name
            ).activity_id,
            external.activity_id,
        )
        self.assertEqual(
            self.executor.schedules[self.pet.name].next_proposal_at,
            150.0,
        )

    def test_hidden_dragged_and_world_mode_changes_interrupt_sleep(self):
        for reason, mutate, world_mode in (
            ("participant_hidden", lambda pet: setattr(pet, "visible", False), "sandbox"),
            ("participant_dragged", lambda pet: setattr(pet, "dragging", True), "sandbox"),
            ("world_mode_changed", lambda pet: None, "golden_legend"),
        ):
            with self.subTest(reason=reason):
                executor, _coordinator = build_executor()
                pet = FakePet("Air Groove")
                executor.update(now=0.0, pets=(pet,), world_mode="sandbox")
                executor.update(now=120.0, pets=(pet,), world_mode="sandbox")
                mutate(pet)

                result = executor.update(
                    now=121.0,
                    pets=(pet,),
                    world_mode=world_mode,
                )[0]

                self.assertTrue(result.interrupted)
                self.assertEqual(result.reason, reason)
                self.assertFalse(pet.activity_state.active)

    def test_user_interrupt_only_handles_sleep_activity(self):
        self.update(0.0)
        self.update(120.0)

        result = self.executor.interrupt_pet(
            self.pet,
            now=121.0,
            reason="user_drag",
        )

        self.assertTrue(result.interrupted)
        self.assertFalse(self.pet.activity_state.active)
        self.assertEqual(
            self.executor.schedules[self.pet.name].next_proposal_at,
            211.0,
        )

    def test_missing_phase_capability_retries_without_starting(self):
        self.pet.asset_manager.missing_context = "activity_sleeping"
        self.update(0.0)

        results = self.update(120.0)

        self.assertEqual(results, ())
        self.assertFalse(self.pet.activity_state.active)
        self.assertEqual(
            self.executor.schedules[self.pet.name].next_proposal_at,
            150.0,
        )


if __name__ == "__main__":
    unittest.main()
