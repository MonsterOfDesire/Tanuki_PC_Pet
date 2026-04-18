import unittest

from tanuki_core.window_perch_rules import (
    advance_window_perch_walk,
    decide_window_perch_mode,
)


class WindowPerchRuleTests(unittest.TestCase):
    def test_decide_window_perch_mode_starts_moving_when_walk_is_available(self):
        decision = decide_window_perch_mode(
            max_offset=80,
            offset_x=10,
            direction=1,
            has_walk_candidates=True,
            move_roll=0.10,
            flip_roll=0.90,
            move_timer=90,
            idle_timer=120,
        )

        self.assertEqual(decision.mode, "move")
        self.assertEqual(decision.state, "move")
        self.assertEqual(decision.state_timer, 90)
        self.assertEqual(decision.direction, 1)
        self.assertTrue(decision.use_walk_animation)

    def test_decide_window_perch_mode_flips_or_idles_when_walk_is_not_selected(self):
        decision = decide_window_perch_mode(
            max_offset=80,
            offset_x=10,
            direction=1,
            has_walk_candidates=True,
            move_roll=0.90,
            flip_roll=0.10,
            move_timer=90,
            idle_timer=120,
        )

        self.assertEqual(decision.mode, "idle")
        self.assertEqual(decision.state, "idle")
        self.assertEqual(decision.state_timer, 120)
        self.assertEqual(decision.direction, -1)
        self.assertFalse(decision.use_walk_animation)

    def test_advance_window_perch_walk_clamps_and_returns_to_idle_at_edges(self):
        left = advance_window_perch_walk(
            offset_x=2,
            direction=-1,
            step=5,
            max_offset=60,
            boundary_idle_timer=70,
        )
        right = advance_window_perch_walk(
            offset_x=58,
            direction=1,
            step=5,
            max_offset=60,
            boundary_idle_timer=80,
        )

        self.assertEqual((left.next_offset, left.direction, left.mode), (0, 1, "idle"))
        self.assertEqual(left.state_timer, 70)
        self.assertEqual((right.next_offset, right.direction, right.mode), (60, -1, "idle"))
        self.assertEqual(right.state_timer, 80)

    def test_advance_window_perch_walk_continues_moving_inside_bounds(self):
        decision = advance_window_perch_walk(
            offset_x=20,
            direction=1,
            step=4,
            max_offset=60,
            boundary_idle_timer=70,
        )

        self.assertEqual(decision.next_offset, 24)
        self.assertEqual(decision.direction, 1)
        self.assertEqual(decision.mode, "move")
        self.assertIsNone(decision.state_timer)


if __name__ == "__main__":
    unittest.main()
