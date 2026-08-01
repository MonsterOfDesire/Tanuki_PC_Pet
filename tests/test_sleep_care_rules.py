import unittest

from tanuki_core.sleep_care_rules import (
    SleepingCaregiverCandidate,
    choose_sleeping_caregiver_to_wake,
)


class SleepCareRuleTests(unittest.TestCase):
    def test_shallow_sleeper_is_preferred_over_nearer_adult(self):
        decision = choose_sleeping_caregiver_to_wake(
            (
                SleepingCaregiverCandidate(
                    "Air Groove",
                    available=True,
                    distance_to_child=20.0,
                ),
                SleepingCaregiverCandidate(
                    "Sirius Symboli",
                    available=True,
                    distance_to_child=400.0,
                    shallow_sleeper=True,
                ),
            ),
            distressed_child_name="Tokai Teio",
            awake_or_responding_caregiver_available=False,
        )

        self.assertTrue(decision.should_wake)
        self.assertEqual(decision.caregiver_name, "Sirius Symboli")
        self.assertEqual(decision.reason, "shallow_sleeper_priority")

    def test_nearest_adult_is_used_when_shallow_sleeper_unavailable(self):
        decision = choose_sleeping_caregiver_to_wake(
            (
                SleepingCaregiverCandidate(
                    "Symboli Rudolf",
                    available=True,
                    distance_to_child=150.0,
                ),
                SleepingCaregiverCandidate(
                    "Air Groove",
                    available=True,
                    distance_to_child=60.0,
                ),
            ),
            distressed_child_name="Tsurumaru Tsuyoshi",
            awake_or_responding_caregiver_available=False,
        )

        self.assertEqual(decision.caregiver_name, "Air Groove")

    def test_awake_caregiver_prevents_sleeping_caregiver_wake(self):
        decision = choose_sleeping_caregiver_to_wake(
            (
                SleepingCaregiverCandidate(
                    "Sirius Symboli",
                    available=True,
                    distance_to_child=20.0,
                    shallow_sleeper=True,
                ),
            ),
            distressed_child_name="Tokai Teio",
            awake_or_responding_caregiver_available=True,
        )

        self.assertFalse(decision.should_wake)
        self.assertEqual(decision.reason, "awake_caregiver_available")


if __name__ == "__main__":
    unittest.main()
