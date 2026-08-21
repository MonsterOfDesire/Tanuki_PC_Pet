import unittest

from tanuki_core.activity_interaction_rules import (
    CHORUS_SLEEP_WAKE_DISTANCE_PX,
    should_chorus_wake_sleeping_pet,
)


class ActivityInteractionRulesTests(unittest.TestCase):
    def test_performing_within_eight_hundred_pixels_wakes_sleeper(self):
        self.assertTrue(
            should_chorus_wake_sleeping_pet(
                distance=CHORUS_SLEEP_WAKE_DISTANCE_PX,
                performer_phase="performing",
                sleeper_phase="sleeping",
            )
        )

    def test_audience_approach_and_distant_performance_do_not_wake(self):
        self.assertFalse(
            should_chorus_wake_sleeping_pet(
                distance=100.0,
                performer_phase="observing",
                sleeper_phase="sleeping",
            )
        )
        self.assertFalse(
            should_chorus_wake_sleeping_pet(
                distance=CHORUS_SLEEP_WAKE_DISTANCE_PX + 0.1,
                performer_phase="performing",
                sleeper_phase="sleeping",
            )
        )


if __name__ == "__main__":
    unittest.main()
