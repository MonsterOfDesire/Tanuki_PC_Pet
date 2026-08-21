import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tanuki_core.runtime_timer_registry import start_runtime_timers


class RuntimeTimerRegistryTests(unittest.TestCase):
    def test_default_registry_preserves_timer_names_and_intervals(self):
        calls = []

        def fake_register(_app, interval_ms, _callback, **kwargs):
            calls.append((interval_ms, kwargs))
            return f"timer-{len(calls)}"

        runtime = SimpleNamespace(
            app=object(),
            pets_list=[],
            profiler=object(),
            logic_scheduler=SimpleNamespace(
                run=lambda *_args, **_kwargs: None,
                resolve_repeat_count=(
                    lambda _pets, default, speed: default
                ),
            ),
            window_tracker=SimpleNamespace(
                available=True,
                refresh=lambda: None,
            ),
            update_offer_scene=lambda: None,
            update_transformations=lambda: None,
            update_race=lambda: None,
            update_chorus=lambda: None,
            update_household_events=lambda: None,
        )

        with patch(
            "tanuki_core.runtime_timer_registry.register_runtime_timer",
            side_effect=fake_register,
        ):
            timers = start_runtime_timers(runtime)

        self.assertEqual(
            tuple(timers),
            (
                "mood",
                "physics",
                "logic",
                "windows",
                "offer",
                "transformation",
                "race",
                "chorus",
                "household",
            ),
        )
        self.assertEqual(
            [interval for interval, _kwargs in calls],
            [3000, 30, 30, 150, 30, 30, 30, 60, 1000],
        )
        self.assertTrue(calls[0][1]["speed_scaled"])
        self.assertEqual(calls[0][1]["minimum_interval_ms"], 250)
        self.assertEqual(calls[6][1]["minimum_interval_ms"], 8)
        self.assertEqual(calls[7][1]["minimum_interval_ms"], 12)
        self.assertEqual(calls[8][1]["minimum_interval_ms"], 250)

    def test_unavailable_window_tracker_does_not_start_poll_timer(self):
        runtime = SimpleNamespace(
            app=object(),
            pets_list=[],
            profiler=object(),
            logic_scheduler=SimpleNamespace(
                run=lambda *_args, **_kwargs: None,
                resolve_repeat_count=(
                    lambda _pets, default, speed: default
                ),
            ),
            window_tracker=SimpleNamespace(
                available=False,
                refresh=lambda: None,
            ),
            update_offer_scene=lambda: None,
            update_transformations=lambda: None,
            update_race=lambda: None,
            update_chorus=lambda: None,
            update_household_events=lambda: None,
        )

        with patch(
            "tanuki_core.runtime_timer_registry.register_runtime_timer",
            return_value=object(),
        ):
            timers = start_runtime_timers(runtime)

        self.assertNotIn("windows", timers)


if __name__ == "__main__":
    unittest.main()
