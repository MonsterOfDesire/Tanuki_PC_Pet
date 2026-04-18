import unittest

from tanuki_core.pet_runtime_state import (
    PET_STATE_PROXY_FIELDS,
    PetBehaviorState,
    PetCareState,
    PetInteractionState,
    PetMotionState,
    PetRuntimeStateBundle,
    PetSocialState,
    PetWindowingState,
    build_pet_runtime_state,
)


class PetRuntimeStateTests(unittest.TestCase):
    def test_behavior_state_defaults_match_pet_widget_expectations(self):
        state = PetBehaviorState()

        self.assertEqual(state.mood_score, 60.0)
        self.assertEqual(state.mood_state, "normal")
        self.assertEqual(state.state, "idle")
        self.assertEqual(state.current_action_tag, "stand")
        self.assertEqual(state.current_mood_tag, "happy")

    def test_interaction_state_defaults_cover_drag_click_lock(self):
        state = PetInteractionState()

        self.assertFalse(state.dragging)
        self.assertEqual(state.drag_start_time, 0.0)
        self.assertEqual(state.click_count, 0)
        self.assertFalse(state.is_angry_locked)
        self.assertTrue(state.user_visible)

    def test_motion_state_defaults_cover_physics_and_movement(self):
        state = PetMotionState()

        self.assertEqual(state.direction, 1)
        self.assertEqual(state.last_x, 0)
        self.assertEqual(state.stuck_count, 0)
        self.assertEqual(state.vy, 0.0)
        self.assertIsNone(state.fall_origin_y)
        self.assertEqual(state.gravity, 1.2)
        self.assertEqual(state.bounce, -0.3)

    def test_social_state_defaults_cover_mode_cooldown_and_distance(self):
        state = PetSocialState()

        self.assertEqual(state.social_mode, "none")
        self.assertIsNone(state.social_target)
        self.assertEqual(state.social_started_at, 0.0)
        self.assertEqual(state.social_timer_frames, 0)
        self.assertEqual(state.social_cooldown_end, 0.0)
        self.assertEqual(state.social_distance, 600)
        self.assertEqual(state.social_cooldown_duration, 5.0)

    def test_care_state_defaults_cover_recovery_and_care_lock(self):
        state = PetCareState()

        self.assertFalse(state.is_recovering)
        self.assertEqual(state.recovery_end_time, 0.0)
        self.assertEqual(state.recovery_motion_mode, "stay")
        self.assertFalse(state.stationary_move_mode)
        self.assertEqual(state.stationary_move_key, "")
        self.assertFalse(state.is_hugging)
        self.assertEqual(state.care_mode, "none")
        self.assertIsNone(state.care_target)
        self.assertEqual(state.care_plan, "auto")
        self.assertIsNone(state.care_partner)
        self.assertEqual(state.care_lock_mode, "none")
        self.assertEqual(state.care_lock_end_time, 0.0)

    def test_windowing_state_defaults_cover_perch_and_flight(self):
        state = PetWindowingState()

        self.assertEqual(state.perched_window_hwnd, 0)
        self.assertEqual(state.window_perch_mode, "idle")
        self.assertEqual(state.flight_mode, "none")
        self.assertEqual(state.flight_target_x, 0)
        self.assertEqual(state.flight_target_y, 0)
        self.assertIsNone(state.movement_state)

    def test_runtime_state_factory_applies_name_specific_social_defaults(self):
        teio_state = build_pet_runtime_state("Tokai Teio")
        tsuyoshi_state = build_pet_runtime_state("Tsurumaru Tsuyoshi")
        rudolf_state = build_pet_runtime_state("Symboli Rudolf")

        self.assertIsInstance(teio_state, PetRuntimeStateBundle)
        self.assertEqual(teio_state.social.social_distance, 600)
        self.assertEqual(teio_state.social.social_cooldown_duration, 10.0)
        self.assertEqual(tsuyoshi_state.social.social_distance, 350)
        self.assertEqual(tsuyoshi_state.social.social_cooldown_duration, 10.0)
        self.assertEqual(rudolf_state.social.social_distance, 600)
        self.assertEqual(rudolf_state.social.social_cooldown_duration, 5.0)

    def test_state_proxy_field_map_covers_runtime_state_groups(self):
        self.assertIn("behavior_state", PET_STATE_PROXY_FIELDS)
        self.assertIn("interaction_state", PET_STATE_PROXY_FIELDS)
        self.assertIn("motion_state", PET_STATE_PROXY_FIELDS)
        self.assertIn("social_state", PET_STATE_PROXY_FIELDS)
        self.assertIn("care_state", PET_STATE_PROXY_FIELDS)
        self.assertIn("windowing_state", PET_STATE_PROXY_FIELDS)
        self.assertIn("mood_score", PET_STATE_PROXY_FIELDS["behavior_state"])
        self.assertIn("care_mode", PET_STATE_PROXY_FIELDS["care_state"])
        self.assertIn("flight_mode", PET_STATE_PROXY_FIELDS["windowing_state"])


if __name__ == "__main__":
    unittest.main()
