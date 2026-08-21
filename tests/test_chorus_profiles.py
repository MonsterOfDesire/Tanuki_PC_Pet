import unittest

from tanuki_core.chorus_profiles import (
    CHORUS_PROFILE,
    evaluate_chorus_capabilities,
)
from tanuki_core.chorus_rules import (
    CHORUS_APPROACH_PHASE,
    CHORUS_FINISH_PHASE,
    CHORUS_OBSERVE_PHASE,
    CHORUS_PERFORM_PHASE,
)


class FakeAssetManager:
    def __init__(self, missing=()):
        self.missing = set(missing)

    def get_contextual_result_for_purposes(
        self,
        purposes,
        context=None,
        preferred_moods=None,
        forbidden=None,
        mood_score=None,
        ordered_preferences=False,
    ):
        if context in self.missing:
            return None
        return ([context], "idle", "manifest-action", "happy")


class ChorusProfilesTests(unittest.TestCase):
    def test_profile_maps_only_manifest_contexts(self):
        self.assertEqual(
            CHORUS_PROFILE.animation_for_phase(
                CHORUS_APPROACH_PHASE
            ).contexts,
            ("activity_chorus_approach",),
        )
        self.assertEqual(
            CHORUS_PROFILE.animation_for_phase(
                CHORUS_PERFORM_PHASE
            ).contexts,
            ("activity_chorus_perform",),
        )
        self.assertEqual(
            CHORUS_PROFILE.animation_for_phase(
                CHORUS_OBSERVE_PHASE
            ).contexts,
            ("activity_chorus_observe",),
        )
        self.assertEqual(
            CHORUS_PROFILE.animation_for_phase(
                CHORUS_FINISH_PHASE
            ).contexts,
            ("activity_chorus_finish",),
        )

    def test_capabilities_keep_optional_finish_separate(self):
        capabilities = evaluate_chorus_capabilities(
            FakeAssetManager(missing={"activity_chorus_finish"}),
            mood_score=60.0,
        )

        self.assertTrue(capabilities.approach)
        self.assertTrue(capabilities.perform)
        self.assertTrue(capabilities.observe)
        self.assertFalse(capabilities.finish)


if __name__ == "__main__":
    unittest.main()
