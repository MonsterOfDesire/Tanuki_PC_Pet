import unittest

from tanuki_core.sleep_profiles import (
    SLEEP_PROFILE,
    evaluate_sleep_capability,
    evaluate_sleep_join_capability,
)
from tanuki_core.sleep_rules import (
    SLEEP_SETTLING_PHASE,
    SLEEP_WAKING_PHASE,
    SLEEPING_PHASE,
)


class FakeAssetManager:
    def __init__(self, available_contexts):
        self.available_contexts = set(available_contexts)

    def get_contextual_result_for_purposes(
        self,
        purposes,
        context=None,
        preferred_moods=None,
        forbidden=None,
        mood_score=None,
        ordered_preferences=False,
    ):
        if context not in self.available_contexts:
            return None
        return ([f"{context}-frame"], "idle", "manifest-action", "sleep")


class SleepProfileTests(unittest.TestCase):
    def test_profile_maps_phases_only_to_manifest_contexts(self):
        expected = {
            SLEEP_SETTLING_PHASE: ("activity_sleep_settling",),
            SLEEPING_PHASE: ("activity_sleeping",),
            SLEEP_WAKING_PHASE: ("activity_sleep_waking",),
        }

        for phase_name, contexts in expected.items():
            binding = SLEEP_PROFILE.animation_for_phase(phase_name)
            self.assertIsNotNone(binding)
            self.assertEqual(binding.contexts, contexts)
            self.assertEqual(binding.band_policy, "match")
            self.assertEqual(binding.fallback_bands, ())

    def test_capability_requires_every_phase_context(self):
        all_contexts = {
            "activity_sleep_settling",
            "activity_sleeping",
            "activity_sleep_waking",
        }
        ready = evaluate_sleep_capability(
            FakeAssetManager(all_contexts),
            mood_score=60.0,
        )
        missing = evaluate_sleep_capability(
            FakeAssetManager(all_contexts - {"activity_sleeping"}),
            mood_score=60.0,
        )

        self.assertTrue(ready.ready)
        self.assertFalse(missing.ready)
        self.assertEqual(missing.phase_name, SLEEPING_PHASE)

    def test_join_profile_uses_manifest_contexts_with_settling_fallback(self):
        self.assertEqual(
            SLEEP_PROFILE.observing_animation.contexts,
            ("activity_sleep_observing",),
        )
        self.assertEqual(
            SLEEP_PROFILE.join_approach_animation.contexts,
            ("activity_sleep_join_approach",),
        )
        self.assertEqual(
            SLEEP_PROFILE.join_settling_animation.contexts,
            (
                "activity_sleep_join_settling",
                "activity_sleep_settling",
            ),
        )

    def test_join_capability_accepts_standard_settling_fallback(self):
        contexts = {
            "activity_sleep_observing",
            "activity_sleep_join_approach",
            "activity_sleep_settling",
            "activity_sleeping",
            "activity_sleep_waking",
        }

        decision = evaluate_sleep_join_capability(
            FakeAssetManager(contexts),
            mood_score=60.0,
        )

        self.assertTrue(decision.ready)


if __name__ == "__main__":
    unittest.main()
