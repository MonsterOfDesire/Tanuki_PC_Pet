import unittest

from tanuki_core.pet_throw_rules import (
    advance_drag_follow,
    advance_horizontal_throw,
    append_drag_motion_sample,
    resolve_throw_launch,
)


class PetThrowRuleTests(unittest.TestCase):
    def test_drag_follow_accelerates_toward_target_without_teleporting(self):
        step = advance_drag_follow(
            current_x=0.0,
            current_y=0.0,
            target_x=100.0,
            target_y=-50.0,
            velocity_x=0.0,
            velocity_y=0.0,
            elapsed_seconds=0.016,
        )

        self.assertGreater(step.x, 0.0)
        self.assertLess(step.x, 100.0)
        self.assertLess(step.y, 0.0)
        self.assertGreater(step.y, -50.0)
        self.assertGreater(step.velocity_x, 0.0)
        self.assertLess(step.velocity_y, 0.0)

    def test_accumulated_drag_velocity_drives_release(self):
        launch = resolve_throw_launch(
            (),
            carried_velocity=(800.0, -400.0),
        )

        self.assertTrue(launch.active)
        self.assertGreater(launch.velocity_x, 0.0)
        self.assertLess(launch.velocity_y, 0.0)

    def test_settled_drag_does_not_throw_from_old_pointer_history(self):
        launch = resolve_throw_launch(
            (
                (1.00, 0.0, 0.0),
                (1.08, 200.0, 0.0),
            ),
            carried_velocity=(0.0, 0.0),
        )

        self.assertFalse(launch.active)

    def test_stationary_hold_does_not_launch(self):
        launch = resolve_throw_launch(
            (
                (1.00, 100.0, 100.0),
                (1.08, 102.0, 100.0),
            )
        )

        self.assertFalse(launch.active)

    def test_fast_flick_produces_bounded_launch_velocity(self):
        launch = resolve_throw_launch(
            (
                (1.00, 100.0, 200.0),
                (1.04, 180.0, 160.0),
                (1.08, 280.0, 100.0),
            )
        )

        self.assertTrue(launch.active)
        self.assertGreater(launch.velocity_x, 0.0)
        self.assertLess(launch.velocity_y, 0.0)
        self.assertLessEqual(abs(launch.velocity_x), 34.0)
        self.assertLessEqual(abs(launch.velocity_y), 28.0)

    def test_sample_history_keeps_one_velocity_anchor_when_events_are_sparse(self):
        samples = append_drag_motion_sample(
            (),
            timestamp=1.0,
            x=0,
            y=0,
        )
        samples = append_drag_motion_sample(
            samples,
            timestamp=1.20,
            x=200,
            y=0,
        )

        self.assertEqual(
            samples,
            (
                (1.0, 0.0, 0.0),
                (1.2, 200.0, 0.0),
            ),
        )

    def test_stationary_release_preserves_recent_flick_velocity(self):
        samples = (
            (1.00, 100.0, 200.0),
            (1.08, 220.0, 160.0),
        )
        samples = append_drag_motion_sample(
            samples,
            timestamp=1.16,
            x=220,
            y=160,
        )

        launch = resolve_throw_launch(samples, released_at=1.16)

        self.assertTrue(launch.active)
        self.assertGreater(launch.velocity_x, 0.0)
        self.assertLess(launch.velocity_y, 0.0)

    def test_old_flick_does_not_launch_after_stationary_hold(self):
        launch = resolve_throw_launch(
            (
                (1.00, 100.0, 200.0),
                (1.08, 220.0, 160.0),
            ),
            released_at=1.40,
        )

        self.assertFalse(launch.active)

    def test_horizontal_throw_bounces_inside_virtual_bounds(self):
        step = advance_horizontal_throw(
            current_x=98,
            velocity_x=8.0,
            remainder_x=0.0,
            left_bound=0,
            right_bound=100,
        )

        self.assertEqual(step.x, 100)
        self.assertLess(step.velocity_x, 0.0)
        self.assertTrue(step.active)

    def test_low_speed_ground_throw_uses_fast_tail_slowdown(self):
        airborne = advance_horizontal_throw(
            current_x=100,
            velocity_x=6.0,
            remainder_x=0.0,
            left_bound=0,
            right_bound=1000,
            grounded=False,
        )
        grounded = advance_horizontal_throw(
            current_x=100,
            velocity_x=6.0,
            remainder_x=0.0,
            left_bound=0,
            right_bound=1000,
            grounded=True,
        )

        self.assertGreater(abs(airborne.velocity_x), abs(grounded.velocity_x))
        self.assertAlmostEqual(airborne.velocity_x, 5.88)
        self.assertAlmostEqual(grounded.velocity_x, 5.16)

    def test_ground_throw_stops_below_half_pixel_per_step(self):
        stopped = advance_horizontal_throw(
            current_x=100,
            velocity_x=0.55,
            remainder_x=0.0,
            left_bound=0,
            right_bound=1000,
            grounded=True,
        )

        self.assertEqual(stopped.velocity_x, 0.0)
        self.assertFalse(stopped.active)


if __name__ == "__main__":
    unittest.main()
