import unittest

from tanuki_core.mood_calibration import (
    DEFAULT_MOOD_CALIBRATION_SCENARIOS,
    MoodCalibrationScenario,
    run_mood_calibration_suite,
    simulate_mood_scenario,
)


class MoodCalibrationTests(unittest.TestCase):
    def test_fixed_seed_produces_repeatable_summary(self):
        scenario = MoodCalibrationScenario(
            name="repeatable",
            climate_key="balanced",
            is_adult=False,
            nearby_count=1,
            has_adult_nearby=True,
            nearest_adult_distance=100.0,
            duration_minutes=10,
        )

        first = simulate_mood_scenario(
            scenario,
            runs=8,
            seed_offset=1234,
        )
        second = simulate_mood_scenario(
            scenario,
            runs=8,
            seed_offset=1234,
        )

        self.assertEqual(first, second)

    def test_balanced_lonely_child_reaches_low_before_severe(self):
        summary = simulate_mood_scenario(
            MoodCalibrationScenario(
                name="lonely",
                climate_key="balanced",
                is_adult=False,
                nearby_count=0,
                has_adult_nearby=False,
                nearest_adult_distance=None,
                duration_minutes=90,
            ),
            runs=40,
            seed_offset=98765,
        )

        self.assertIsNotNone(summary.median_first_low_minutes)
        self.assertIsNotNone(summary.median_first_severe_minutes)
        self.assertLess(
            summary.median_first_low_minutes,
            summary.median_first_severe_minutes,
        )

    def test_household_timeline_models_sleep_and_chorus_rewards(self):
        summary = simulate_mood_scenario(
            MoodCalibrationScenario(
                name="activity_timeline",
                climate_key="balanced",
                is_adult=False,
                nearby_count=4,
                has_adult_nearby=True,
                nearest_adult_distance=140.0,
                duration_minutes=60,
                simulate_sleep=True,
                simulate_chorus=True,
                chorus_mood_reward=2.0,
            ),
            runs=20,
            seed_offset=321,
        )

        self.assertGreater(summary.activity_paused_percent, 0.0)
        self.assertGreater(summary.sleep_completions_per_hour, 0.0)
        self.assertGreater(summary.chorus_completions_per_hour, 0.0)
        self.assertGreater(summary.activity_mood_gain_per_hour, 0.0)

    def test_balanced_household_can_reach_low_despite_activity_rewards(self):
        summary = simulate_mood_scenario(
            DEFAULT_MOOD_CALIBRATION_SCENARIOS[0],
            runs=120,
            seed_offset=240801,
        )

        self.assertGreater(summary.low_percent, 5.0)
        self.assertEqual(summary.severe_percent, 0.0)
        self.assertGreater(
            summary.entered_low_by_60_minutes_percent,
            45.0,
        )
        self.assertLess(summary.average_final_score, 60.0)

    def test_default_scenario_seed_is_stable_when_cli_filters_scenarios(self):
        scenario = DEFAULT_MOOD_CALIBRATION_SCENARIOS[1]

        filtered = run_mood_calibration_suite(
            runs=8,
            scenarios=(scenario,),
        )[0]
        complete = run_mood_calibration_suite(runs=8)[1]

        self.assertEqual(filtered, complete)


if __name__ == "__main__":
    unittest.main()
