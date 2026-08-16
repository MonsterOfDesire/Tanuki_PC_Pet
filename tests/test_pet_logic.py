import unittest

from tanuki_core.pet_logic import (
    AI_FOLLOWUP_CARE,
    AI_FOLLOWUP_CARE_LOCK,
    AI_FOLLOWUP_RANDOM,
    AI_FOLLOWUP_SOCIAL,
    AI_PHASE_ANGRY_LOCKED,
    AI_PHASE_NORMAL,
    AI_PHASE_RECOVERY_ACTIVE,
    AI_PHASE_RECOVERY_FINISHED,
    CLICK_RELEASE,
    DRAG_RELEASE,
    LONG_HOLD_RELEASE,
    compute_mood_update,
    decide_followup_ai_phase,
    decide_initial_ai_phase,
    decide_release_interaction,
    decide_tick_phase,
    derive_mood_state,
    natural_mood_update_is_paused,
    TICK_PHASE_AIRBORNE,
    TICK_PHASE_DRAGGING,
    TICK_PHASE_RUN_AI,
    TICK_PHASE_WINDOW_FLIGHT,
    TICK_PHASE_WINDOW_PERCH,
)
from tanuki_core.settings_provider import RuntimeSettings


class MoodLogicTests(unittest.TestCase):
    def test_sleep_and_chorus_pause_only_natural_mood_ticks(self):
        self.assertTrue(
            natural_mood_update_is_paused(
                activity_kind="sleep",
                activity_active=True,
            )
        )
        self.assertTrue(
            natural_mood_update_is_paused(
                activity_kind="chorus",
                activity_active=True,
            )
        )
        self.assertFalse(
            natural_mood_update_is_paused(
                activity_kind="race",
                activity_active=True,
            )
        )
        self.assertFalse(
            natural_mood_update_is_paused(
                activity_kind="sleep",
                activity_active=False,
            )
        )

    def test_adult_without_neighbors_recovers_slightly(self):
        update = compute_mood_update(
            current_score=60.0,
            lonely_timer=0,
            is_adult=True,
            nearby_count=0,
            has_adult_nearby=False,
            noise=0.0,
        )

        self.assertEqual(update.lonely_timer, 0)
        self.assertEqual(update.mood_score, 60.5)
        self.assertEqual(update.mood_state, "normal")

    def test_child_without_neighbors_accumulates_loneliness_penalty(self):
        update = compute_mood_update(
            current_score=60.0,
            lonely_timer=9,
            is_adult=False,
            nearby_count=0,
            has_adult_nearby=False,
            noise=0.0,
        )

        self.assertEqual(update.lonely_timer, 12)
        self.assertEqual(update.mood_score, 59.0)
        self.assertEqual(update.mood_state, "normal")

    def test_child_nearby_adult_gets_social_bonus_and_resets_lonely_timer(self):
        update = compute_mood_update(
            current_score=40.0,
            lonely_timer=6,
            is_adult=False,
            nearby_count=1,
            has_adult_nearby=True,
            noise=0.0,
        )

        self.assertEqual(update.lonely_timer, 0)
        self.assertEqual(update.mood_score, 43.5)
        self.assertEqual(update.mood_state, "unhappy")

    def test_derive_mood_state_thresholds(self):
        self.assertEqual(derive_mood_state(10), "depressed")
        self.assertEqual(derive_mood_state(25), "unhappy")
        self.assertEqual(derive_mood_state(80), "normal")

    def test_expressive_climate_does_not_pull_low_mood_toward_a_target(self):
        update = compute_mood_update(
            current_score=30.0,
            lonely_timer=0,
            is_adult=True,
            nearby_count=2,
            has_adult_nearby=True,
            climate_key="expressive",
            change_roll=0.0,
            direction_roll=0.0,
            magnitude_roll=0.5,
        )

        self.assertLess(update.mood_score, 30.0)

    def test_cheerful_climate_skips_most_natural_mood_ticks(self):
        update = compute_mood_update(
            current_score=40.0,
            lonely_timer=0,
            is_adult=True,
            nearby_count=0,
            has_adult_nearby=False,
            climate_key="cheerful",
            change_roll=0.75,
            direction_roll=1.0,
            magnitude_roll=1.0,
        )

        self.assertEqual(update.mood_score, 40.0)

    def test_balanced_changes_more_often_than_old_low_frequency_model(self):
        update = compute_mood_update(
            current_score=45.0,
            lonely_timer=0,
            is_adult=True,
            nearby_count=0,
            has_adult_nearby=False,
            climate_key="balanced",
            change_roll=0.60,
            direction_roll=1.0,
            magnitude_roll=1.0,
        )

        self.assertGreater(update.mood_score, 45.0)

    def test_expressive_negative_change_is_larger_than_cheerful(self):
        common = dict(
            current_score=70.0,
            lonely_timer=0,
            is_adult=True,
            nearby_count=0,
            has_adult_nearby=False,
            change_roll=0.0,
            direction_roll=0.0,
            magnitude_roll=1.0,
        )

        cheerful = compute_mood_update(
            **common,
            climate_key="cheerful",
        )
        expressive = compute_mood_update(
            **common,
            climate_key="expressive",
        )

        self.assertGreater(cheerful.mood_score, expressive.mood_score)

    def test_expressive_child_far_from_adult_loses_mood_faster(self):
        common = dict(
            current_score=70.0,
            lonely_timer=9,
            is_adult=False,
            nearby_count=0,
            has_adult_nearby=False,
            climate_key="expressive",
            change_roll=0.0,
            direction_roll=0.0,
            magnitude_roll=1.0,
        )

        far = compute_mood_update(
            **common,
            nearest_adult_distance=1500.0,
        )
        close = compute_mood_update(
            **common,
            nearest_adult_distance=320.0,
        )

        self.assertLess(far.mood_score, close.mood_score)

    def test_expressive_adult_negative_change_is_damped(self):
        common = dict(
            current_score=70.0,
            lonely_timer=9,
            nearby_count=0,
            has_adult_nearby=False,
            climate_key="expressive",
            change_roll=0.0,
            direction_roll=0.0,
            magnitude_roll=1.0,
            nearest_adult_distance=1500.0,
        )

        adult = compute_mood_update(**common, is_adult=True)
        child = compute_mood_update(**common, is_adult=False)

        self.assertGreater(adult.mood_score, child.mood_score)

    def test_expressive_severe_adult_can_self_regulate_upward(self):
        common = dict(
            lonely_timer=0,
            is_adult=True,
            nearby_count=0,
            has_adult_nearby=False,
            climate_key="expressive",
            change_roll=0.0,
            direction_roll=0.40,
            magnitude_roll=0.5,
        )

        normal = compute_mood_update(current_score=60.0, **common)
        severe = compute_mood_update(current_score=10.0, **common)

        self.assertLess(normal.mood_score, 60.0)
        self.assertGreater(severe.mood_score, 10.0)

    def test_cheerful_positive_change_is_not_a_target_based_jump(self):
        update = compute_mood_update(
            current_score=10.0,
            lonely_timer=0,
            is_adult=True,
            nearby_count=0,
            has_adult_nearby=False,
            climate_key="cheerful",
            change_roll=0.0,
            direction_roll=1.0,
            magnitude_roll=1.0,
        )

        self.assertEqual(update.mood_score, 10.6)


class ReleaseDecisionTests(unittest.TestCase):
    def test_click_release_increments_clicks_and_rewards_pet(self):
        decision = decide_release_interaction(duration=0.1, click_count=1)

        self.assertEqual(decision.kind, CLICK_RELEASE)
        self.assertEqual(decision.next_click_count, 2)
        self.assertEqual(decision.mood_delta, 8.0)
        self.assertTrue(decision.starts_click_reset_timer)
        self.assertFalse(decision.triggers_angry_lock)

    def test_click_release_can_trigger_angry_lock(self):
        decision = decide_release_interaction(duration=0.1, click_count=4)

        self.assertEqual(decision.kind, CLICK_RELEASE)
        self.assertEqual(decision.next_click_count, 5)
        self.assertEqual(decision.mood_delta, -60.0)
        self.assertTrue(decision.triggers_angry_lock)

    def test_long_hold_release_applies_penalty_without_click_timer(self):
        decision = decide_release_interaction(duration=5.1, click_count=2)

        self.assertEqual(decision.kind, LONG_HOLD_RELEASE)
        self.assertEqual(decision.next_click_count, 2)
        self.assertEqual(decision.mood_delta, -25.0)
        self.assertFalse(decision.starts_click_reset_timer)

    def test_regular_drag_release_keeps_neutral_outcome(self):
        decision = decide_release_interaction(duration=1.0, click_count=3)

        self.assertEqual(decision.kind, DRAG_RELEASE)
        self.assertEqual(decision.next_click_count, 3)
        self.assertEqual(decision.mood_delta, 0.0)
        self.assertFalse(decision.starts_click_reset_timer)
        self.assertFalse(decision.triggers_angry_lock)


class TickDecisionTests(unittest.TestCase):
    def test_dragging_has_highest_tick_priority(self):
        phase = decide_tick_phase(
            dragging=True,
            window_perch_handled=True,
            window_flight_handled=True,
            vertical_velocity=0,
        )
        self.assertEqual(phase, TICK_PHASE_DRAGGING)

    def test_window_perch_short_circuits_before_other_motion(self):
        phase = decide_tick_phase(
            dragging=False,
            window_perch_handled=True,
            window_flight_handled=False,
            vertical_velocity=0,
        )
        self.assertEqual(phase, TICK_PHASE_WINDOW_PERCH)

    def test_window_flight_short_circuits_before_edge(self):
        phase = decide_tick_phase(
            dragging=False,
            window_perch_handled=False,
            window_flight_handled=True,
            vertical_velocity=0,
        )
        self.assertEqual(phase, TICK_PHASE_WINDOW_FLIGHT)

    def test_grounded_tick_runs_ai(self):
        phase = decide_tick_phase(
            dragging=False,
            window_perch_handled=False,
            window_flight_handled=False,
            vertical_velocity=0,
        )
        self.assertEqual(phase, TICK_PHASE_RUN_AI)

    def test_airborne_tick_skips_ai(self):
        phase = decide_tick_phase(
            dragging=False,
            window_perch_handled=False,
            window_flight_handled=False,
            vertical_velocity=1.5,
        )
        self.assertEqual(phase, TICK_PHASE_AIRBORNE)


class AiDecisionTests(unittest.TestCase):
    def test_angry_lock_has_highest_ai_priority(self):
        phase = decide_initial_ai_phase(
            is_angry_locked=True,
            is_recovering=True,
            recovery_expired=True,
        )
        self.assertEqual(phase, AI_PHASE_ANGRY_LOCKED)

    def test_recovery_active_blocks_followup_ai(self):
        phase = decide_initial_ai_phase(
            is_angry_locked=False,
            is_recovering=True,
            recovery_expired=False,
        )
        self.assertEqual(phase, AI_PHASE_RECOVERY_ACTIVE)

    def test_recovery_finished_reenters_normal_flow(self):
        phase = decide_initial_ai_phase(
            is_angry_locked=False,
            is_recovering=True,
            recovery_expired=True,
        )
        self.assertEqual(phase, AI_PHASE_RECOVERY_FINISHED)

    def test_normal_ai_phase_when_unlocked(self):
        phase = decide_initial_ai_phase(
            is_angry_locked=False,
            is_recovering=False,
            recovery_expired=False,
        )
        self.assertEqual(phase, AI_PHASE_NORMAL)

    def test_care_lock_precedes_other_followup_behaviors(self):
        phase = decide_followup_ai_phase(
            care_lock_maintained=True,
            care_behavior_handled=True,
            social_behavior_handled=True,
        )
        self.assertEqual(phase, AI_FOLLOWUP_CARE_LOCK)

    def test_care_precedes_social(self):
        phase = decide_followup_ai_phase(
            care_lock_maintained=False,
            care_behavior_handled=True,
            social_behavior_handled=True,
        )
        self.assertEqual(phase, AI_FOLLOWUP_CARE)

    def test_social_precedes_random(self):
        phase = decide_followup_ai_phase(
            care_lock_maintained=False,
            care_behavior_handled=False,
            social_behavior_handled=True,
        )
        self.assertEqual(phase, AI_FOLLOWUP_SOCIAL)

    def test_random_is_last_followup_phase(self):
        phase = decide_followup_ai_phase(
            care_lock_maintained=False,
            care_behavior_handled=False,
            social_behavior_handled=False,
        )
        self.assertEqual(phase, AI_FOLLOWUP_RANDOM)


class RuntimeSettingsTests(unittest.TestCase):
    def test_default_settings_match_dashboard_defaults(self):
        settings = RuntimeSettings()

        self.assertTrue(settings.care_feature_enabled)
        self.assertFalse(settings.debug_enabled)
        self.assertFalse(settings.social_status_enabled)
        self.assertEqual(settings.get_time_scale(), 1.0)
        self.assertEqual(settings.get_display_scale_multiplier(), 1.0)

    def test_social_cooldowns_follow_character_indices(self):
        settings = RuntimeSettings(teio_dur_idx=1, tsuyoshi_dur_idx=4)

        self.assertEqual(settings.get_social_cooldown_seconds("Tokai Teio"), 5.0)
        self.assertEqual(settings.get_social_cooldown_seconds("Tsurumaru Tsuyoshi"), 60.0)
        self.assertEqual(settings.get_social_cooldown_seconds("Symboli Rudolf"), 0.0)


if __name__ == "__main__":
    unittest.main()
