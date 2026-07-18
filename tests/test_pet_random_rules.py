import unittest

from tanuki_core.pet_random_rules import (
    NORMAL_RANDOM_DIRECTION_FLIP_CHANCE,
    SEVERE_RANDOM_DIRECTION_FLIP_CHANCE,
    build_random_state_transition,
    derive_random_visual_purpose,
    extend_random_state_timer,
    get_idle_action_override,
    resolve_random_stuck_behavior,
    should_refresh_severe_random_state,
)


class PetRandomRuleTests(unittest.TestCase):
    def test_severe_state_refreshes_when_mood_not_severe(self):
        self.assertTrue(should_refresh_severe_random_state("sad", {"cry", "scold"}, 50))

    def test_severe_state_refreshes_when_timer_expires(self):
        self.assertTrue(should_refresh_severe_random_state("cry", {"cry", "scold"}, 0))

    def test_random_transition_flips_when_roll_is_under_threshold(self):
        transition = build_random_state_transition(
            next_state="move",
            next_state_timer=120,
            flip_roll=0.2,
            flip_threshold=NORMAL_RANDOM_DIRECTION_FLIP_CHANCE,
        )

        self.assertEqual(transition.next_state, "move")
        self.assertEqual(transition.next_state_timer, 120)
        self.assertTrue(transition.flip_direction)

    def test_stuck_resolution_reverses_direction_after_threshold(self):
        resolution = resolve_random_stuck_behavior(
            stationary_move_mode=False,
            position_delta=0.0,
            stuck_count=60,
            recovery_state_timer=44,
        )

        self.assertTrue(resolution.flip_direction)
        self.assertEqual(resolution.next_state_timer, 44)
        self.assertEqual(resolution.next_stuck_count, 0)

    def test_stationary_move_resets_stuck_count(self):
        resolution = resolve_random_stuck_behavior(
            stationary_move_mode=True,
            position_delta=0.0,
            stuck_count=12,
            recovery_state_timer=50,
        )

        self.assertFalse(resolution.flip_direction)
        self.assertEqual(resolution.next_stuck_count, 0)

    def test_visual_purpose_requires_enough_speed_for_move(self):
        self.assertEqual(derive_random_visual_purpose("move", 1.2), "move")
        self.assertEqual(derive_random_visual_purpose("move", 0.8), "idle")
        self.assertEqual(derive_random_visual_purpose("idle", 2.0), "idle")

    def test_extend_random_state_timer_holds_current_state(self):
        self.assertEqual(extend_random_state_timer(-3, 30), 30)
        self.assertEqual(extend_random_state_timer(42, 30), 42)

    def test_tsuyoshi_side_stand_requires_side_ready_first(self):
        self.assertEqual(
            get_idle_action_override(
                "Tsurumaru Tsuyoshi",
                current_purpose="idle",
                current_action_tag="stand",
                next_purpose="idle",
                next_action_tag="side_stand",
            ),
            ("side_ready", "side", "stand"),
        )
        self.assertEqual(
            get_idle_action_override(
                "Tsurumaru Tsuyoshi",
                current_purpose="idle",
                current_action_tag="side_ready",
                next_purpose="idle",
                next_action_tag="side_stand",
            ),
            (),
        )
        self.assertEqual(
            get_idle_action_override(
                "Symboli Rudolf",
                current_purpose="idle",
                current_action_tag="stand",
                next_purpose="idle",
                next_action_tag="side_stand",
            ),
            (),
        )


if __name__ == "__main__":
    unittest.main()
