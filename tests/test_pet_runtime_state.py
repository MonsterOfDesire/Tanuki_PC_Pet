import unittest

from tanuki_core.pet_runtime_state import (
    PET_STATE_PROXY_FIELDS,
    PetBehaviorState,
    PetCareState,
    PetExpressionState,
    PetInteractionState,
    PetIntentState,
    PetMotionState,
    PetPerceptionState,
    PetRelationshipState,
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
        self.assertEqual(state.last_company_seen_at, 0.0)
        self.assertEqual(state.solitude_event_cooldown_until, 0.0)
        self.assertEqual(state.crowding_event_cooldown_until, 0.0)
        self.assertEqual(state.offer_miss_event_cooldown_until, 0.0)
        self.assertFalse(state.idle_side_stand_armed)
        self.assertEqual(state.behavior_layer_refresh_skip_counter, 0)
        self.assertEqual(state.behavior_layer_refresh_divisor, 1)
        self.assertEqual(state.high_level_ai_refresh_skip_counter, 0)
        self.assertEqual(state.high_level_ai_refresh_divisor, 1)

    def test_interaction_state_defaults_cover_drag_click_lock(self):
        state = PetInteractionState()

        self.assertFalse(state.dragging)
        self.assertFalse(state.drag_press_pending)
        self.assertFalse(state.drag_motion_detected)
        self.assertEqual(state.drag_press_global_x, 0)
        self.assertEqual(state.drag_press_global_y, 0)
        self.assertEqual(state.drag_start_time, 0.0)
        self.assertEqual(state.click_count, 0)
        self.assertFalse(state.is_angry_locked)
        self.assertTrue(state.user_visible)
        self.assertEqual(state.held_item_kind, "")
        self.assertEqual(state.held_item_source, "none")
        self.assertEqual(state.held_item_started_at, 0.0)
        self.assertIsNone(state.held_item_widget)
        self.assertEqual(state.negative_afterglow_until, 0.0)
        self.assertEqual(state.negative_afterglow_care_block_until, 0.0)
        self.assertEqual(state.negative_afterglow_preferred_moods, ())
        self.assertEqual(state.negative_afterglow_forbidden_moods, ())
        self.assertEqual(state.offer_hover_reaction_cooldown_until, 0.0)

    def test_motion_state_defaults_cover_physics_and_movement(self):
        state = PetMotionState()

        self.assertEqual(state.direction, 1)
        self.assertEqual(state.last_x, 0)
        self.assertEqual(state.stuck_count, 0)
        self.assertEqual(state.vy, 0.0)
        self.assertEqual(state.collision_displaced_until, 0.0)
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

    def test_perception_intent_relationship_and_expression_defaults_are_initialized(self):
        perception = PetPerceptionState()
        intent = PetIntentState()
        relationship = PetRelationshipState()
        expression = PetExpressionState()

        self.assertEqual(perception.perception_anchor, "floor")
        self.assertEqual(perception.perception_situation_tag, "stable")
        self.assertEqual(intent.intent_kind, "none")
        self.assertEqual(intent.intent_context, "ambient")
        self.assertEqual(intent.observe_blocked_target_name, "")
        self.assertEqual(intent.observe_blocked_until, 0.0)
        self.assertEqual(intent.observe_streak_target_name, "")
        self.assertEqual(intent.observe_streak_count, 0)
        self.assertEqual(intent.pending_social_log_event, {})
        self.assertEqual(intent.social_log_event_cooldown_until, 0.0)
        self.assertEqual(relationship.relationship_entries, {})
        self.assertEqual(expression.expression_animation_context, "ambient")
        self.assertEqual(expression.expression_relation_overlay, "none")

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
        self.assertEqual(teio_state.intent.intent_kind, "none")
        self.assertEqual(teio_state.expression.expression_animation_context, "ambient")
        self.assertFalse(teio_state.activity.active)

    def test_state_proxy_field_map_covers_runtime_state_groups(self):
        self.assertIn("behavior_state", PET_STATE_PROXY_FIELDS)
        self.assertIn("interaction_state", PET_STATE_PROXY_FIELDS)
        self.assertIn("motion_state", PET_STATE_PROXY_FIELDS)
        self.assertIn("social_state", PET_STATE_PROXY_FIELDS)
        self.assertIn("care_state", PET_STATE_PROXY_FIELDS)
        self.assertIn("windowing_state", PET_STATE_PROXY_FIELDS)
        self.assertIn("perception_state", PET_STATE_PROXY_FIELDS)
        self.assertIn("intent_state", PET_STATE_PROXY_FIELDS)
        self.assertIn("relationship_state", PET_STATE_PROXY_FIELDS)
        self.assertIn("expression_state", PET_STATE_PROXY_FIELDS)
        self.assertIn("mood_score", PET_STATE_PROXY_FIELDS["behavior_state"])
        self.assertIn("last_company_seen_at", PET_STATE_PROXY_FIELDS["behavior_state"])
        self.assertIn("solitude_event_cooldown_until", PET_STATE_PROXY_FIELDS["behavior_state"])
        self.assertIn("crowding_event_cooldown_until", PET_STATE_PROXY_FIELDS["behavior_state"])
        self.assertIn("offer_miss_event_cooldown_until", PET_STATE_PROXY_FIELDS["behavior_state"])
        self.assertIn("idle_side_stand_armed", PET_STATE_PROXY_FIELDS["behavior_state"])
        self.assertIn("behavior_layer_refresh_skip_counter", PET_STATE_PROXY_FIELDS["behavior_state"])
        self.assertIn("behavior_layer_refresh_divisor", PET_STATE_PROXY_FIELDS["behavior_state"])
        self.assertIn("high_level_ai_refresh_skip_counter", PET_STATE_PROXY_FIELDS["behavior_state"])
        self.assertIn("high_level_ai_refresh_divisor", PET_STATE_PROXY_FIELDS["behavior_state"])
        self.assertIn("care_mode", PET_STATE_PROXY_FIELDS["care_state"])
        self.assertIn("flight_mode", PET_STATE_PROXY_FIELDS["windowing_state"])
        self.assertIn("collision_displaced_until", PET_STATE_PROXY_FIELDS["motion_state"])
        self.assertIn("intent_kind", PET_STATE_PROXY_FIELDS["intent_state"])
        self.assertIn("observe_blocked_target_name", PET_STATE_PROXY_FIELDS["intent_state"])
        self.assertIn("observe_streak_target_name", PET_STATE_PROXY_FIELDS["intent_state"])
        self.assertIn("observe_streak_count", PET_STATE_PROXY_FIELDS["intent_state"])
        self.assertIn("pending_social_log_event", PET_STATE_PROXY_FIELDS["intent_state"])
        self.assertIn("social_log_event_cooldown_until", PET_STATE_PROXY_FIELDS["intent_state"])
        self.assertIn("expression_animation_context", PET_STATE_PROXY_FIELDS["expression_state"])
        self.assertIn("held_item_kind", PET_STATE_PROXY_FIELDS["interaction_state"])
        self.assertIn("drag_press_pending", PET_STATE_PROXY_FIELDS["interaction_state"])
        self.assertIn("drag_motion_detected", PET_STATE_PROXY_FIELDS["interaction_state"])
        self.assertIn("drag_press_global_x", PET_STATE_PROXY_FIELDS["interaction_state"])
        self.assertIn("drag_press_global_y", PET_STATE_PROXY_FIELDS["interaction_state"])
        self.assertIn("held_item_widget", PET_STATE_PROXY_FIELDS["interaction_state"])
        self.assertIn("negative_afterglow_until", PET_STATE_PROXY_FIELDS["interaction_state"])
        self.assertIn("negative_afterglow_care_block_until", PET_STATE_PROXY_FIELDS["interaction_state"])
        self.assertIn("negative_afterglow_preferred_moods", PET_STATE_PROXY_FIELDS["interaction_state"])
        self.assertIn("offer_hover_reaction_cooldown_until", PET_STATE_PROXY_FIELDS["interaction_state"])


if __name__ == "__main__":
    unittest.main()
