import unittest

from tanuki_core.pet_throw_rules import (
    advance_horizontal_throw,
    append_drag_motion_sample,
    resolve_throw_launch,
)


class PetThrowRuleTests(unittest.TestCase):
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
        self.assertLessEqual(abs(launch.velocity_x), 26.0)
        self.assertLessEqual(abs(launch.velocity_y), 22.0)

    def test_sample_history_drops_stale_motion(self):
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

        self.assertEqual(samples, ((1.2, 200.0, 0.0),))

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


if __name__ == "__main__":
    unittest.main()
