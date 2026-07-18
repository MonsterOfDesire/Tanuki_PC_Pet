import unittest

from tanuki_core.pet_intent_rules import INTENT_OBSERVE
from tanuki_core.pet_observe_rules import (
    POST_OBSERVE_INTERACTION_CLOSE_DURATION,
    POST_OBSERVE_INTERACTION_CHANCE_MIN,
    POST_OBSERVE_INTERACTION_MAX_DISTANCE,
    resolve_post_observe_interaction_candidate,
    resolve_observe_reentry_cooldown,
    resolve_observe_plan,
    resolve_observe_same_target_cooldown,
    resolve_observe_start_decision,
    resolve_observe_target_notice_decision,
    resolve_post_observe_escape,
    should_pause_observe_backoff,
)


class ObserveRuleTests(unittest.TestCase):
    def test_observe_plan_starts_lock_and_holds_idle_for_relation_watch(self):
        plan = resolve_observe_plan(
            now=10.0,
            intent_kind="ambient_idle",
            locked_target_name="",
            intent_locked_until=0.0,
            intent_reconsider_after=0.0,
            focus_target_name="Symboli Rudolf",
            expression_animation_context="relation_watch",
            target_visible=True,
            target_distance=180.0,
            target_dx=60.0,
        )

        self.assertTrue(plan.handled)
        self.assertEqual(plan.target_name, "Symboli Rudolf")
        self.assertTrue(plan.should_hold_idle)
        self.assertEqual(plan.desired_direction, 1)
        self.assertGreater(plan.lock_until, 10.0)

    def test_observe_plan_uses_backoff_when_target_is_too_close(self):
        plan = resolve_observe_plan(
            now=10.0,
            intent_kind=INTENT_OBSERVE,
            locked_target_name="Air Groove",
            intent_locked_until=12.0,
            intent_reconsider_after=0.0,
            focus_target_name="Symboli Rudolf",
            expression_animation_context="relation_close",
            target_visible=True,
            target_distance=80.0,
            target_dx=40.0,
        )

        self.assertTrue(plan.handled)
        self.assertTrue(plan.should_backoff)
        self.assertEqual(plan.desired_direction, -1)
        self.assertEqual(plan.target_name, "Air Groove")
        self.assertEqual(plan.lock_until, 12.0)

    def test_observe_plan_clears_lock_when_target_is_missing_or_far(self):
        missing = resolve_observe_plan(
            now=10.0,
            intent_kind=INTENT_OBSERVE,
            locked_target_name="Tokai Teio",
            intent_locked_until=12.0,
            intent_reconsider_after=0.0,
            focus_target_name="Tokai Teio",
            expression_animation_context="relation_watch",
            target_visible=False,
            target_distance=0.0,
            target_dx=0.0,
        )
        far = resolve_observe_plan(
            now=10.0,
            intent_kind=INTENT_OBSERVE,
            locked_target_name="Tokai Teio",
            intent_locked_until=12.0,
            intent_reconsider_after=0.0,
            focus_target_name="Tokai Teio",
            expression_animation_context="relation_watch",
            target_visible=True,
            target_distance=500.0,
            target_dx=0.0,
        )

        self.assertFalse(missing.handled)
        self.assertTrue(missing.clear_lock)
        self.assertFalse(far.handled)
        self.assertTrue(far.clear_lock)

    def test_observe_plan_does_not_start_for_far_focus_or_during_cooldown(self):
        far = resolve_observe_plan(
            now=10.0,
            intent_kind="ambient_idle",
            locked_target_name="",
            intent_locked_until=0.0,
            intent_reconsider_after=0.0,
            focus_target_name="Tokai Teio",
            expression_animation_context="relation_watch",
            target_visible=True,
            target_distance=300.0,
            target_dx=0.0,
        )
        cooling = resolve_observe_plan(
            now=10.0,
            intent_kind="ambient_idle",
            locked_target_name="",
            intent_locked_until=0.0,
            intent_reconsider_after=10.5,
            focus_target_name="Tokai Teio",
            expression_animation_context="relation_watch",
            target_visible=True,
            target_distance=160.0,
            target_dx=0.0,
        )

        self.assertFalse(far.handled)
        self.assertFalse(far.clear_lock)
        self.assertFalse(cooling.handled)

    def test_observe_plan_clears_expired_observe_lock_during_cooldown(self):
        cooling = resolve_observe_plan(
            now=10.0,
            intent_kind=INTENT_OBSERVE,
            locked_target_name="Tokai Teio",
            intent_locked_until=9.5,
            intent_reconsider_after=10.5,
            focus_target_name="Tokai Teio",
            expression_animation_context="relation_watch",
            target_visible=True,
            target_distance=160.0,
            target_dx=0.0,
        )

        self.assertFalse(cooling.handled)
        self.assertTrue(cooling.clear_lock)

    def test_should_pause_observe_backoff_when_any_side_was_recently_displaced(self):
        self.assertTrue(should_pause_observe_backoff(
            now=10.0,
            subject_collision_displaced_until=10.2,
            target_collision_displaced_until=0.0,
        ))
        self.assertTrue(should_pause_observe_backoff(
            now=10.0,
            subject_collision_displaced_until=0.0,
            target_collision_displaced_until=10.2,
        ))
        self.assertFalse(should_pause_observe_backoff(
            now=10.0,
            subject_collision_displaced_until=9.8,
            target_collision_displaced_until=9.9,
        ))

    def test_same_target_cooldown_grows_with_consecutive_observe_streak(self):
        first_cooldown, first_target, first_streak = resolve_observe_same_target_cooldown(
            previous_target_name="Tokai Teio",
            streak_target_name="",
            streak_count=0,
        )
        repeat_cooldown, repeat_target, repeat_streak = resolve_observe_same_target_cooldown(
            previous_target_name="Tokai Teio",
            streak_target_name=first_target,
            streak_count=first_streak,
        )

        self.assertEqual(first_target, "Tokai Teio")
        self.assertEqual(first_streak, 1)
        self.assertGreater(first_cooldown, 0.0)
        self.assertEqual(repeat_target, "Tokai Teio")
        self.assertEqual(repeat_streak, 2)
        self.assertGreater(repeat_cooldown, first_cooldown)

    def test_same_target_cooldown_and_reentry_cooldown_gain_crowd_bonus(self):
        solo_cooldown, _, solo_streak = resolve_observe_same_target_cooldown(
            previous_target_name="Tokai Teio",
            streak_target_name="",
            streak_count=0,
            visible_pet_count=1,
        )
        crowd_cooldown, _, crowd_streak = resolve_observe_same_target_cooldown(
            previous_target_name="Tokai Teio",
            streak_target_name="",
            streak_count=0,
            visible_pet_count=4,
        )
        solo_reentry = resolve_observe_reentry_cooldown(
            visible_pet_count=1,
            streak_count=solo_streak,
        )
        crowd_reentry = resolve_observe_reentry_cooldown(
            visible_pet_count=4,
            streak_count=crowd_streak,
        )

        self.assertGreater(crowd_cooldown, solo_cooldown)
        self.assertGreater(crowd_reentry, solo_reentry)

    def test_post_observe_escape_prefers_moving_away_from_previous_target(self):
        should_escape, direction, state_timer = resolve_post_observe_escape(
            previous_target_name="Tokai Teio",
            previous_target_dx=80.0,
            current_direction=1,
            visible_pet_count=4,
            streak_count=2,
            roll=0.0,
        )

        self.assertTrue(should_escape)
        self.assertEqual(direction, -1)
        self.assertGreaterEqual(state_timer, 140)

    def test_observe_start_decision_is_probabilistic_and_penalized_by_crowd_and_streak(self):
        allowed = resolve_observe_start_decision(
            expression_animation_context="relation_watch",
            visible_pet_count=1,
            streak_count=0,
            roll=0.0,
        )
        skipped = resolve_observe_start_decision(
            expression_animation_context="relation_watch",
            visible_pet_count=4,
            streak_count=3,
            roll=0.99,
        )

        self.assertTrue(allowed.should_start)
        self.assertFalse(skipped.should_start)
        self.assertGreater(skipped.retry_cooldown, 0.0)
        self.assertEqual(skipped.reason, "observe_start_skipped")

    def test_post_observe_interaction_candidate_prefers_close_short_followup(self):
        decision = resolve_post_observe_interaction_candidate(
            previous_target_name="Tokai Teio",
            target_visible=True,
            target_distance=90.0,
            expression_animation_context="relation_close",
            visible_pet_count=1,
            streak_count=0,
            roll=0.0,
        )

        self.assertTrue(decision.should_start)
        self.assertEqual(decision.interaction_context, "relation_close")
        self.assertEqual(decision.lock_duration, POST_OBSERVE_INTERACTION_CLOSE_DURATION)

    def test_post_observe_interaction_allows_slightly_wider_followup_range(self):
        near_edge = resolve_post_observe_interaction_candidate(
            previous_target_name="Tokai Teio",
            target_visible=True,
            target_distance=POST_OBSERVE_INTERACTION_MAX_DISTANCE,
            expression_animation_context="relation_watch",
            visible_pet_count=1,
            streak_count=0,
            roll=0.0,
        )
        too_far = resolve_post_observe_interaction_candidate(
            previous_target_name="Tokai Teio",
            target_visible=True,
            target_distance=POST_OBSERVE_INTERACTION_MAX_DISTANCE + 1.0,
            expression_animation_context="relation_watch",
            visible_pet_count=1,
            streak_count=0,
            roll=0.0,
        )

        self.assertTrue(near_edge.should_start)
        self.assertFalse(too_far.should_start)
        self.assertEqual(too_far.reason, "target_out_of_range")

    def test_post_observe_interaction_keeps_minimum_chance_under_penalties(self):
        allowed_at_floor = resolve_post_observe_interaction_candidate(
            previous_target_name="Tokai Teio",
            target_visible=True,
            target_distance=100.0,
            expression_animation_context="relation_watch",
            visible_pet_count=8,
            streak_count=20,
            roll=POST_OBSERVE_INTERACTION_CHANCE_MIN - 0.01,
        )
        skipped_at_floor = resolve_post_observe_interaction_candidate(
            previous_target_name="Tokai Teio",
            target_visible=True,
            target_distance=100.0,
            expression_animation_context="relation_watch",
            visible_pet_count=8,
            streak_count=20,
            roll=POST_OBSERVE_INTERACTION_CHANCE_MIN,
        )

        self.assertTrue(allowed_at_floor.should_start)
        self.assertFalse(skipped_at_floor.should_start)
        self.assertEqual(skipped_at_floor.reason, "post_observe_interaction_skipped")

    def test_post_observe_interaction_candidate_skips_when_target_is_far_or_roll_fails(self):
        far = resolve_post_observe_interaction_candidate(
            previous_target_name="Tokai Teio",
            target_visible=True,
            target_distance=220.0,
            expression_animation_context="relation_watch",
            visible_pet_count=1,
            streak_count=0,
            roll=0.0,
        )
        skipped = resolve_post_observe_interaction_candidate(
            previous_target_name="Tokai Teio",
            target_visible=True,
            target_distance=100.0,
            expression_animation_context="relation_watch",
            visible_pet_count=3,
            streak_count=2,
            roll=0.99,
        )

        self.assertFalse(far.should_start)
        self.assertEqual(far.reason, "target_out_of_range")
        self.assertFalse(skipped.should_start)
        self.assertEqual(skipped.reason, "post_observe_interaction_skipped")

    def test_observe_target_notice_is_probabilistic_and_respects_busy_or_cooldown(self):
        allowed = resolve_observe_target_notice_decision(
            now=10.0,
            target_busy=False,
            cooldown_until=0.0,
            visible_pet_count=1,
            roll=0.0,
        )
        busy = resolve_observe_target_notice_decision(
            now=10.0,
            target_busy=True,
            cooldown_until=0.0,
            visible_pet_count=1,
            roll=0.0,
        )
        cooling = resolve_observe_target_notice_decision(
            now=10.0,
            target_busy=False,
            cooldown_until=11.0,
            visible_pet_count=1,
            roll=0.0,
        )
        skipped = resolve_observe_target_notice_decision(
            now=10.0,
            target_busy=False,
            cooldown_until=0.0,
            visible_pet_count=4,
            roll=0.99,
        )

        self.assertTrue(allowed.should_notice)
        self.assertGreater(allowed.duration, 0.0)
        self.assertGreater(allowed.cooldown, 0.0)
        self.assertFalse(busy.should_notice)
        self.assertEqual(busy.reason, "target_busy")
        self.assertFalse(cooling.should_notice)
        self.assertEqual(cooling.reason, "target_notice_cooldown")
        self.assertFalse(skipped.should_notice)
        self.assertEqual(skipped.reason, "target_notice_skipped")


if __name__ == "__main__":
    unittest.main()
