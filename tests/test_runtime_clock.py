import unittest

from tanuki_core.runtime import SimulationClock


class RuntimeTests(unittest.TestCase):
    def test_fast_logic_timers_scale_to_dense_real_time_updates(self):
        clock = SimulationClock()
        clock.speed = 8.0

        self.assertEqual(clock.get_timer_interval(30, minimum_interval_ms=8), 8)
        self.assertEqual(clock.get_timer_repeat_count(30, minimum_interval_ms=8), 2)

    def test_animation_timer_matches_legacy_speed_scaled_refresh(self):
        clock = SimulationClock()
        clock.speed = 8.0

        self.assertEqual(clock.get_timer_interval(80), 10)
        self.assertEqual(clock.get_timer_repeat_count(80), 1)
        self.assertAlmostEqual(clock.get_timer_step_delta(80), 1.0)

    def test_medium_timers_still_scale_cleanly(self):
        clock = SimulationClock()
        clock.speed = 8.0

        self.assertEqual(clock.get_timer_interval(150), 19)
        self.assertEqual(clock.get_timer_repeat_count(150), 1)
        self.assertAlmostEqual(clock.get_timer_step_delta(150), 1.0133333333)

    def test_register_and_speed_change_reapply_timer_interval(self):
        clock = SimulationClock()
        timer = FakeTimer()

        clock.register_timer(timer, 30)
        clock.set_speed(4.0)

        self.assertEqual(timer.intervals[0], 30)
        self.assertEqual(timer.intervals[-1], 8)

    def test_custom_minimum_interval_can_be_provided_for_specific_timers(self):
        clock = SimulationClock()
        timer = FakeTimer()

        clock.register_timer(timer, 30, minimum_interval_ms=8)
        clock.set_speed(8.0)

        self.assertEqual(timer.intervals[-1], 8)


class FakeTimer:
    def __init__(self):
        self.intervals = []

    def setInterval(self, interval):
        self.intervals.append(interval)


if __name__ == "__main__":
    unittest.main()
