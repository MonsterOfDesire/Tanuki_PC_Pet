import unittest

from tanuki_core.activity_profiles import ActivityAnimationBinding
from tanuki_core.manifest_animation_resolver import (
    BAND_POLICY_IGNORE,
    BAND_POLICY_MATCH,
)


class ActivityAnimationBindingTests(unittest.TestCase):
    def test_match_policy_uses_current_band_before_declared_fallbacks(self):
        binding = ActivityAnimationBinding(
            contexts=("activity_work_stationary",),
            fallback_bands=("normal",),
        )

        request = binding.build_request(35.0)

        self.assertEqual(request.contexts, ("activity_work_stationary",))
        self.assertEqual(request.band_policy, BAND_POLICY_MATCH)
        self.assertEqual(request.band_order, ("low", "normal"))

    def test_ignore_policy_builds_request_without_band_order(self):
        binding = ActivityAnimationBinding(
            contexts=("activity_work_rest",),
            band_policy=BAND_POLICY_IGNORE,
        )

        request = binding.build_request(90.0)

        self.assertEqual(request.contexts, ("activity_work_rest",))
        self.assertEqual(request.band_policy, BAND_POLICY_IGNORE)
        self.assertEqual(request.band_order, ())

    def test_binding_rejects_empty_context_or_ignore_fallback(self):
        with self.assertRaises(ValueError):
            ActivityAnimationBinding(contexts=())
        with self.assertRaises(ValueError):
            ActivityAnimationBinding(
                contexts=("activity_work_rest",),
                band_policy=BAND_POLICY_IGNORE,
                fallback_bands=("normal",),
            )


if __name__ == "__main__":
    unittest.main()
