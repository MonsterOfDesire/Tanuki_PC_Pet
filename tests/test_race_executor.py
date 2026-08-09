import unittest

from tanuki_core.activity_coordinator import ActivityCoordinator
from tanuki_core.activity_runtime_adapter import ActivityRuntimeAdapter
from tanuki_core.activity_state import PetActivityState
from tanuki_core.race_executor import RaceExecutor
from tanuki_core.race_rules import (
    RACE_FINISH_PHASE,
    RACE_READY_PHASE,
    RACE_RECOVERY_PHASE,
    RACE_RESPONSE_PHASE,
    RACE_RUNNING_PHASE,
    RACE_TO_START_PHASE,
)
from tanuki_core.race_state import RaceScheduleState
from tanuki_core.transformation_state import PetTransformationState


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
        return ([f"{context}-frame"], "move", "manifest-action", "manifest-mood")


class FakePet:
    def __init__(self, name, *, mood_score=60.0, is_adult=True):
        self.name = name
        self.mood_score = mood_score
        self.is_adult = is_adult
        self.asset_manager = FakeAssetManager()
        self.activity_state = PetActivityState()
        self.transformation_state = PetTransformationState()
        self.dragging = False
        self.drag_press_pending = False
        self.is_angry_locked = False
        self.is_recovering = False
        self.care_mode = "none"
        self.care_partner = None
        self.social_mode = "none"
        self.social_cooldown_end = 999.0
        self.intent_kind = "none"
        self.intent_reconsider_after = 999.0
        self.observe_blocked_target_name = ""
        self.observe_blocked_until = 0.0
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
        self.direction = 1
        self._x = 100.0
        self.move_step = None
        self.apply_calls = []
        self.distressed = False
        self.post_race_interactions = []
        self.radius = 50.0
        self.honor_min_speed = False
        self.movement_steps = []

    def isVisible(self):
        return self.visible

    def is_under_care(self, now):
        return False

    def is_offer_locked(self, now):
        return False

    def is_distressed(self):
        return self.distressed

    def apply_animation_result(self, purpose, result):
        self.apply_calls.append((purpose, result))
        return True

    def refresh_movement_state(self):
        return None

    def x(self):
        return self._x

    def width(self):
        return 100

    def move_toward_x(self, target_x, speed_scale=1.0, min_speed=None):
        target_x = float(target_x)
        if self.honor_min_speed:
            step = abs(float(min_speed or 0.0)) * float(speed_scale)
            self.movement_steps.append(step)
            distance = target_x - self._x
            if abs(distance) <= step:
                self._x = target_x
                return True
            self._x += step if distance > 0.0 else -step
            return False
        if self.move_step is None:
            self._x = target_x
            return True
        distance = target_x - self._x
        step = abs(float(self.move_step))
        if abs(distance) <= step:
            self._x = target_x
            return True
        self._x += step if distance > 0.0 else -step
        return False

    def start_post_observe_interaction(
        self,
        target,
        now,
        interaction_context,
        lock_duration,
    ):
        self.post_race_interactions.append(
            (
                target.name,
                float(now),
                interaction_context,
                float(lock_duration),
            )
        )
        return True


def build_executor(random_values=(0.0, 0.0, 0.0, 0.0)):
    sequence = iter(range(1, 100))
    rolls = iter(random_values)
    coordinator = ActivityCoordinator(
        activity_id_factory=lambda: f"race-{next(sequence)}",
        event_id_factory=lambda: f"event-{next(sequence)}",
    )
    executor = RaceExecutor(
        coordinator=coordinator,
        runtime_adapter=ActivityRuntimeAdapter(),
        schedule=RaceScheduleState(next_proposal_at=10.0),
        uniform=lambda minimum, maximum: minimum,
        random_value=lambda: next(rolls, 0.0),
        bounds_provider=lambda pets: (0.0, 900.0),
    )
    return executor, coordinator


class RaceExecutorTests(unittest.TestCase):
    def setUp(self):
        self.executor, self.coordinator = build_executor()
        self.rudolf = FakePet("Symboli Rudolf")
        self.teio = FakePet("Tokai Teio", is_adult=False)
        self.rudolf._x = 100.0
        self.teio._x = 350.0
        self.pets = (self.rudolf, self.teio)
        self.events = []

    def update(self, now, **overrides):
        arguments = {
            "now": now,
            "world_mode": "golden_legend",
            "pets": self.pets,
            "record_race_event": self.events.append,
        }
        arguments.update(overrides)
        return self.executor.update(**arguments)

    def advance_to_running(self):
        started = self.update(10.0)
        self.assertTrue(started.started)
        self.update(12.0)
        self.assertEqual(self.rudolf.activity_state.phase, RACE_RESPONSE_PHASE)
        self.update(14.0)
        self.assertEqual(self.rudolf.activity_state.phase, RACE_TO_START_PHASE)
        self.update(14.1)
        self.assertEqual(self.rudolf.activity_state.phase, RACE_READY_PHASE)
        self.update(16.1)
        self.assertEqual(self.rudolf.activity_state.phase, RACE_RUNNING_PHASE)

    def test_complete_race_uses_manifest_phases_and_records_one_event(self):
        self.advance_to_running()
        active = self.coordinator.get_active_activities()[0]
        self.assertEqual(active.metadata["race_course_key"], "practice_100m")
        self.assertEqual(active.metadata["race_distance"], 500.0)

        self.update(16.2)
        self.assertEqual(self.rudolf.activity_state.phase, RACE_FINISH_PHASE)
        self.update(19.2)
        self.assertEqual(self.rudolf.activity_state.phase, RACE_RECOVERY_PHASE)
        finished = self.update(23.2)

        self.assertTrue(finished.finished)
        self.assertFalse(self.rudolf.activity_state.active)
        self.assertFalse(self.teio.activity_state.active)
        self.assertEqual(len(self.events), 1)
        self.assertEqual(self.events[0].event_type, "race_completed")
        self.assertEqual(self.events[0].winner_name, "Tokai Teio")
        self.assertEqual(self.events[0].race_course_key, "practice_100m")
        self.assertEqual(self.events[0].race_nominal_meters, 100)
        self.assertIn(
            ("activity_race_finish_lose", 60.0),
            self.rudolf.asset_manager.calls,
        )
        self.assertIn(
            ("activity_race_finish_win", 60.0),
            self.teio.asset_manager.calls,
        )
        self.assertEqual(
            self.rudolf.post_race_interactions,
            [("Tokai Teio", 23.2, "relation_watch", 1.6)],
        )
        self.assertEqual(
            self.teio.post_race_interactions,
            [("Symboli Rudolf", 23.2, "relation_watch", 1.6)],
        )
        self.assertEqual(self.rudolf.social_cooldown_end, 23.2)
        self.assertEqual(self.teio.intent_reconsider_after, 23.2)

    def test_challenge_plays_consider_animation_on_opponent_immediately(self):
        started = self.update(10.0)

        self.assertTrue(started.started)
        self.assertIn(
            ("activity_race_challenge", 60.0),
            self.rudolf.asset_manager.calls,
        )
        self.assertIn(
            ("activity_race_consider", 60.0),
            self.teio.asset_manager.calls,
        )

    def test_dragging_one_participant_releases_both_racers(self):
        started = self.update(10.0)
        self.assertTrue(started.started)

        interrupted = self.executor.interrupt_pet(
            self.teio,
            now=10.1,
            reason="user_drag",
            pets=self.pets,
        )

        self.assertTrue(interrupted.interrupted)
        self.assertFalse(self.rudolf.activity_state.active)
        self.assertFalse(self.teio.activity_state.active)

    def test_hidden_participant_interrupts_and_releases_both_racers(self):
        started = self.update(10.0)
        self.assertTrue(started.started)
        self.teio.visible = False

        interrupted = self.update(10.1)

        self.assertTrue(interrupted.interrupted)
        self.assertEqual(interrupted.reason, "participant_hidden")
        self.assertFalse(self.rudolf.activity_state.active)
        self.assertFalse(self.teio.activity_state.active)

    def test_ready_phase_faces_the_same_direction_as_running(self):
        self.rudolf._x = 550.0
        self.teio._x = 800.0
        self.update(10.0)
        self.update(12.0)
        self.update(14.0)
        self.update(14.1)

        self.assertEqual(self.rudolf.activity_state.phase, RACE_READY_PHASE)
        activity = self.coordinator.get_active_activities()[0]
        expected_direction = int(activity.metadata["race_direction"])
        self.assertEqual(self.rudolf.direction, expected_direction)
        self.assertEqual(self.teio.direction, expected_direction)

    def test_adult_losing_to_teio_uses_normal_finish_band(self):
        self.executor, self.coordinator = build_executor(
            (0.0, 0.0, 0.0, 0.0, 1.0)
        )
        self.advance_to_running()

        self.update(16.2)

        self.assertIn(
            ("activity_race_finish_lose", 60.0),
            self.rudolf.asset_manager.calls,
        )
        self.assertIn(
            ("activity_race_finish_win", 60.0),
            self.teio.asset_manager.calls,
        )

    def test_far_apart_participants_cannot_start_a_remote_challenge(self):
        self.rudolf._x = 100.0
        self.teio._x = 600.1

        result = self.update(10.0)

        self.assertFalse(result.started)
        self.assertEqual(result.reason, "participants_too_far")
        self.assertFalse(self.rudolf.activity_state.active)
        self.assertFalse(self.teio.activity_state.active)

    def test_overlapping_participants_wait_before_starting_a_challenge(self):
        self.rudolf._x = 100.0
        self.teio._x = 150.0

        result = self.update(10.0)

        self.assertFalse(result.started)
        self.assertEqual(result.reason, "participants_too_close")

    def test_to_start_replans_instead_of_timing_out_when_progress_stalls(self):
        self.rudolf.move_step = 0.0
        self.teio.move_step = 0.0
        self.update(10.0)
        self.update(12.0)
        self.update(14.0)

        stalled = self.update(50.0)

        self.assertTrue(stalled.handled)
        self.assertFalse(stalled.interrupted)
        self.assertEqual(self.rudolf.activity_state.phase, RACE_TO_START_PHASE)
        activity = self.coordinator.get_active_activities()[0]
        self.assertEqual(activity.metadata["to_start_last_progress_at"], 50.0)
        self.assertEqual(activity.metadata["race_course_key"], "practice_100m")
        self.assertEqual(activity.metadata["race_distance"], 500.0)

    def test_full_lane_uses_course_roll_and_keeps_discrete_1500px_distance(self):
        self.executor, self.coordinator = build_executor(
            (0.0, 0.0, 0.0, 0.0, 0.0, 0.85)
        )
        self.executor.bounds_provider = lambda pets: (0.0, 2400.0)

        started = self.update(10.0)

        self.assertTrue(started.started)
        activity = self.coordinator.get_active_activities()[0]
        self.assertEqual(activity.metadata["race_course_key"], "practice_800m")
        self.assertEqual(activity.metadata["race_nominal_meters"], 800)
        self.assertEqual(activity.metadata["race_distance"], 1500.0)

    def test_winner_waits_for_loser_to_regroup_before_finish_phase(self):
        self.advance_to_running()
        activity = self.coordinator.get_active_activities()[0]
        winner_finish_x = float(activity.metadata["opponent_finish_x"])
        direction = int(activity.metadata["race_direction"])
        winner = self.teio
        loser = self.rudolf
        winner._x = winner_finish_x
        loser._x = winner_finish_x - (direction * 300.0)
        winner.move_step = 20.0
        loser.move_step = 20.0

        still_running = self.update(16.2)

        self.assertFalse(still_running.phase_changed)
        self.assertEqual(self.rudolf.activity_state.phase, RACE_RUNNING_PHASE)
        self.assertIn(
            ("activity_race_finish_win", 60.0),
            winner.asset_manager.calls,
        )
        self.assertEqual(winner.direction, -direction)
        self.assertEqual(loser.direction, direction)
        loser._x = winner_finish_x - (direction * 140.0)

        regrouped = self.update(16.3)

        self.assertTrue(regrouped.phase_changed)
        self.assertEqual(self.rudolf.activity_state.phase, RACE_FINISH_PHASE)
        self.assertEqual(winner.direction, -direction)
        self.assertEqual(loser.direction, direction)

    def test_child_distress_immediately_interrupts_race_for_care(self):
        self.advance_to_running()
        child = FakePet("Tsurumaru Tsuyoshi", is_adult=False)
        child.distressed = True

        result = self.update(16.2, pets=(*self.pets, child))

        self.assertTrue(result.interrupted)
        self.assertEqual(result.reason, "child_care_needed")
        self.assertFalse(self.rudolf.activity_state.active)
        self.assertEqual(self.events, [])

    def test_tsuyoshi_honey_immediately_interrupts_race_for_guardian(self):
        self.advance_to_running()
        child = FakePet("Tsurumaru Tsuyoshi", is_adult=False)
        child.held_item_kind = "honey"

        result = self.update(16.2, pets=(*self.pets, child))

        self.assertTrue(result.interrupted)
        self.assertEqual(result.reason, "tsuyoshi_honey_guard_needed")
        self.assertEqual(self.events, [])

    def test_bottle_food_sleep_or_work_elsewhere_does_not_interrupt(self):
        self.advance_to_running()
        child = FakePet("Tsurumaru Tsuyoshi", is_adult=False)
        child.held_item_kind = "bottle"
        child.offer_scene_kind = "bottle_feed"
        child.activity_state.activity_id = "other-activity"
        child.activity_state.activity_kind = "sleep"

        result = self.update(16.2, pets=(*self.pets, child))

        self.assertFalse(result.interrupted)
        self.assertEqual(self.rudolf.activity_state.phase, RACE_FINISH_PHASE)

    def test_sandbox_preview_runs_without_event_or_formal_schedule_change(self):
        executor, _coordinator = build_executor((0.0,))
        initial_schedule = executor.schedule.next_proposal_at

        started = executor.start_preview(
            now=5.0,
            world_mode="sandbox",
            rudolf_pet=self.rudolf,
            teio_pet=self.teio,
        )

        self.assertTrue(started.started)
        self.assertTrue(executor.is_preview_active())
        executor.update(
            now=7.0,
            world_mode="sandbox",
            pets=self.pets,
            record_race_event=self.events.append,
        )
        self.assertEqual(self.events, [])
        self.assertEqual(executor.schedule.next_proposal_at, initial_schedule)

    def test_sandbox_autonomous_race_uses_the_formal_schedule_and_records_event(self):
        started = self.update(10.0, world_mode="sandbox")
        self.assertTrue(started.started)

        for now in (12.0, 14.0, 14.1, 16.1, 16.2, 19.2, 23.2):
            result = self.update(now, world_mode="sandbox")

        self.assertTrue(result.finished)
        self.assertEqual(len(self.events), 1)
        self.assertEqual(self.events[0].world_mode, "sandbox")
        self.assertEqual(self.events[0].execution_mode, "autonomous")
        self.assertGreater(self.executor.schedule.next_proposal_at, 23.2)

    def test_fractional_race_steps_accumulate_without_losing_average_speed(self):
        self.advance_to_running()
        activity = self.coordinator.get_active_activities()[0]
        self.rudolf._x = 0.0
        self.rudolf.honor_min_speed = True

        for _index in range(10):
            self.executor._move_pet_precise(
                activity,
                self.rudolf,
                1000.0,
                speed=8.8,
                remainder_key="challenger_move_remainder",
            )

        self.assertEqual(self.rudolf._x, 88.0)
        self.assertEqual(set(self.rudolf.movement_steps), {8.0, 9.0})
        self.assertAlmostEqual(
            activity.metadata["challenger_move_remainder"],
            0.0,
            places=6,
        )

    def test_actual_first_arrival_decides_the_winner(self):
        self.advance_to_running()
        self.rudolf.honor_min_speed = True
        self.teio.honor_min_speed = True

        now = 16.2
        for _index in range(100):
            result = self.update(now)
            activity = self.coordinator.get_active_activities()[0]
            if activity.metadata.get("winner_name"):
                break
            now += 0.05

        self.assertEqual(activity.metadata["winner_name"], "Tokai Teio")
        self.assertGreater(activity.metadata["race_elapsed_seconds"], 0.0)


if __name__ == "__main__":
    unittest.main()
