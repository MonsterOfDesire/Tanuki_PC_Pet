import unittest

from tanuki_core.window_motion import (
    compute_flight_step,
    compute_perch_collision_x,
    get_window_flight_speed,
    get_window_perch_speed,
)


class WindowMotionTests(unittest.TestCase):
    def test_window_perch_speed_scales_from_base_speed(self):
        self.assertEqual(get_window_perch_speed(1.0), 1)
        self.assertEqual(get_window_perch_speed(4.0), 3)

    def test_window_flight_speed_has_minimum(self):
        self.assertEqual(get_window_flight_speed(0.5), 2.6)
        self.assertAlmostEqual(get_window_flight_speed(3.0), 4.1)

    def test_compute_flight_step_arrives_when_close_enough(self):
        next_x, next_y, arrived = compute_flight_step(
            current_x=10,
            current_y=10,
            target_x=16,
            target_y=12,
            speed=5.0,
            time_value=1.0,
            frame_index=0,
            left_bound=0,
            right_bound=100,
            bottom_bound=100,
            min_y=0,
        )

        self.assertEqual((next_x, next_y), (16, 12))
        self.assertTrue(arrived)

    def test_compute_flight_step_clamps_to_bounds_when_travelling(self):
        next_x, next_y, arrived = compute_flight_step(
            current_x=95,
            current_y=50,
            target_x=200,
            target_y=200,
            speed=20.0,
            time_value=1.0,
            frame_index=3,
            left_bound=0,
            right_bound=100,
            bottom_bound=80,
            min_y=10,
        )

        self.assertFalse(arrived)
        self.assertLessEqual(next_x, 100)
        self.assertLessEqual(next_y, 80)
        self.assertGreaterEqual(next_y, 10)

    def test_compute_perch_collision_x_clamps_inside_surface(self):
        self.assertEqual(compute_perch_collision_x(100, 20, 80, 140), 120)
        self.assertEqual(compute_perch_collision_x(100, -50, 80, 140), 80)
        self.assertEqual(compute_perch_collision_x(100, 80, 80, 140), 140)


if __name__ == "__main__":
    unittest.main()
