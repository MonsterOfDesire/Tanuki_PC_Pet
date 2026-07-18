import unittest

from tanuki_core.pet_logic import (
    AI_FOLLOWUP_RANDOM,
    AI_PHASE_RECOVERY_FINISHED,
    TICK_PHASE_AIRBORNE,
    TICK_PHASE_DRAGGING,
    TICK_PHASE_RUN_AI,
)
from tanuki_core.pet_tick_coordinator import PetTickCoordinator


class PetTickCoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.coordinator = PetTickCoordinator()

    def test_dragging_skips_window_attempts(self):
        plan = self.coordinator.build_tick_window_plan(dragging=True)

        self.assertFalse(plan.try_window_perch)
        self.assertFalse(plan.try_window_flight)

    def test_grounded_tick_runs_ai_after_physics_checks(self):
        plan = self.coordinator.resolve_tick_execution_plan(
            dragging=False,
            window_perch_handled=False,
            window_flight_handled=False,
            vertical_velocity=0.0,
        )

        self.assertEqual(plan.phase, TICK_PHASE_RUN_AI)
        self.assertTrue(plan.should_apply_gravity)
        self.assertTrue(plan.should_check_boundary_stuck)
        self.assertTrue(plan.should_run_ai)
        self.assertFalse(plan.should_refresh_and_return)

    def test_dragging_tick_returns_early(self):
        plan = self.coordinator.resolve_tick_execution_plan(
            dragging=True,
            window_perch_handled=False,
            window_flight_handled=False,
            vertical_velocity=0.0,
        )

        self.assertEqual(plan.phase, TICK_PHASE_DRAGGING)
        self.assertFalse(plan.should_apply_gravity)
        self.assertFalse(plan.should_run_ai)
        self.assertTrue(plan.should_refresh_and_return)

    def test_airborne_tick_skips_ai_but_keeps_physics(self):
        plan = self.coordinator.resolve_tick_execution_plan(
            dragging=False,
            window_perch_handled=False,
            window_flight_handled=False,
            vertical_velocity=2.0,
        )

        self.assertEqual(plan.phase, TICK_PHASE_AIRBORNE)
        self.assertTrue(plan.should_apply_gravity)
        self.assertFalse(plan.should_run_ai)

    def test_recovery_active_walk_refreshes_without_followup(self):
        plan = self.coordinator.resolve_initial_ai_plan(
            is_angry_locked=False,
            is_recovering=True,
            recovery_expired=False,
            recovery_motion_mode="walk",
            current_purpose="move",
        )

        self.assertTrue(plan.should_move_recovery_walk)
        self.assertFalse(plan.should_attempt_followup)
        self.assertTrue(plan.should_refresh_and_return)

    def test_recovery_finished_resets_and_reenters_followup(self):
        plan = self.coordinator.resolve_initial_ai_plan(
            is_angry_locked=False,
            is_recovering=True,
            recovery_expired=True,
            recovery_motion_mode="stay",
            current_purpose="idle",
        )

        self.assertEqual(plan.phase, AI_PHASE_RECOVERY_FINISHED)
        self.assertTrue(plan.should_finish_recovery)
        self.assertTrue(plan.should_attempt_followup)
        self.assertFalse(plan.should_refresh_and_return)

    def test_followup_random_only_runs_random(self):
        plan = self.coordinator.resolve_followup_ai_plan(
            care_lock_maintained=False,
            care_behavior_handled=False,
            social_behavior_handled=False,
        )

        self.assertEqual(plan.phase, AI_FOLLOWUP_RANDOM)
        self.assertTrue(plan.should_run_random)
        self.assertFalse(plan.should_refresh_and_return)

    def test_intent_reselect_plan_only_opens_for_ambient_states(self):
        blocked = self.coordinator.resolve_intent_reselect_plan(
            now=5.0,
            intent_kind="perch_hold",
            intent_reconsider_after=0.0,
            dragging=False,
            is_angry_locked=False,
            is_recovering=False,
            care_lock_maintained=False,
            care_mode="none",
            social_mode="none",
            flight_mode="none",
            perched_window_hwnd=1,
        )
        allowed = self.coordinator.resolve_intent_reselect_plan(
            now=5.0,
            intent_kind="random_roam",
            intent_reconsider_after=0.0,
            dragging=False,
            is_angry_locked=False,
            is_recovering=False,
            care_lock_maintained=False,
            care_mode="none",
            social_mode="none",
            flight_mode="none",
            perched_window_hwnd=0,
        )

        self.assertFalse(blocked.allow_reselect)
        self.assertEqual(blocked.reason, "perched")
        self.assertTrue(allowed.allow_reselect)
        self.assertGreater(allowed.next_reconsider_after, 5.0)


if __name__ == "__main__":
    unittest.main()
