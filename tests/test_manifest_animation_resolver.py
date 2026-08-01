import unittest

from tanuki_core.manifest_animation_resolver import (
    BAND_POLICY_IGNORE,
    ManifestAnimationRequest,
    ManifestAnimationResolver,
)


class FakeAssetManager:
    def __init__(self, results=None):
        self.results = dict(results or {})
        self.calls = []

    def get_contextual_result_for_purposes(
        self,
        purposes,
        context=None,
        preferred_moods=None,
        forbidden=None,
        mood_score=None,
        ordered_preferences=False,
    ):
        self.calls.append(
            {
                "purposes": tuple(purposes),
                "context": context,
                "preferred_moods": preferred_moods,
                "forbidden": forbidden,
                "mood_score": mood_score,
                "ordered_preferences": ordered_preferences,
            }
        )
        return self.results.get((context, mood_score))


class FakePet:
    def __init__(self, asset_manager=None, apply_result=True):
        self.asset_manager = asset_manager
        self.apply_result = apply_result
        self.apply_calls = []

    def apply_animation_result(self, purpose, result):
        self.apply_calls.append((purpose, result))
        return self.apply_result


class ManifestAnimationRequestTests(unittest.TestCase):
    def test_request_normalizes_duplicates_and_rejects_unknown_band(self):
        request = ManifestAnimationRequest(
            contexts=("activity_work", "", "activity_work"),
            band_order=("low", "normal", "low"),
        )

        self.assertEqual(request.contexts, ("activity_work",))
        self.assertEqual(request.band_order, ("low", "normal"))

        with self.assertRaises(ValueError):
            ManifestAnimationRequest(
                contexts=("activity_work",),
                band_order=("nornal",),
            )

    def test_request_requires_context_and_band(self):
        with self.assertRaises(ValueError):
            ManifestAnimationRequest(contexts=(), band_order=("normal",))
        with self.assertRaises(ValueError):
            ManifestAnimationRequest(contexts=("activity_work",), band_order=())

    def test_ignore_band_policy_requires_no_band_order(self):
        request = ManifestAnimationRequest(
            contexts=("activity_work_rest",),
            band_policy=BAND_POLICY_IGNORE,
        )

        self.assertEqual(request.band_order, ())
        self.assertEqual(request.band_policy, BAND_POLICY_IGNORE)

        with self.assertRaises(ValueError):
            ManifestAnimationRequest(
                contexts=("activity_work_rest",),
                band_order=("low",),
                band_policy=BAND_POLICY_IGNORE,
            )


class ManifestAnimationResolverTests(unittest.TestCase):
    def test_resolver_uses_only_context_band_and_manifest_weighted_selector(self):
        manager = FakeAssetManager(
            {
                ("activity_work", 30.0): (
                    ["work-frame"],
                    "move",
                    "manifest_selected_action",
                    "effort",
                )
            }
        )
        resolver = ManifestAnimationResolver()

        result = resolver.resolve(
            manager,
            ManifestAnimationRequest(
                contexts=("activity_work",),
                band_order=("low",),
            ),
        )

        self.assertTrue(result.found)
        self.assertEqual(result.selection.context, "activity_work")
        self.assertEqual(result.selection.band_policy, "match")
        self.assertEqual(result.selection.band, "low")
        self.assertEqual(result.selection.purpose, "move")
        self.assertEqual(result.selection.action_type, "manifest_selected_action")
        self.assertEqual(
            manager.calls,
            [
                {
                    "purposes": ("idle", "move"),
                    "context": "activity_work",
                    "preferred_moods": None,
                    "forbidden": None,
                    "mood_score": 30.0,
                    "ordered_preferences": False,
                }
            ],
        )

    def test_resolver_tries_context_then_band_fallback_order(self):
        manager = FakeAssetManager(
            {
                ("activity_work_fallback", 60.0): (
                    ["rest-frame"],
                    "idle",
                    "manifest_rest",
                    "happy",
                )
            }
        )
        resolver = ManifestAnimationResolver()

        result = resolver.resolve(
            manager,
            ManifestAnimationRequest(
                contexts=("activity_work_primary", "activity_work_fallback"),
                band_order=("severe", "normal"),
            ),
        )

        self.assertTrue(result.found)
        self.assertEqual(result.selection.context, "activity_work_fallback")
        self.assertEqual(result.selection.band, "normal")
        self.assertEqual(
            [(call["context"], call["mood_score"]) for call in manager.calls],
            [
                ("activity_work_primary", 0.0),
                ("activity_work_primary", 60.0),
                ("activity_work_fallback", 0.0),
                ("activity_work_fallback", 60.0),
            ],
        )

    def test_resolver_reports_missing_manifest_match_without_action_fallback(self):
        manager = FakeAssetManager()

        result = ManifestAnimationResolver().resolve(
            manager,
            ManifestAnimationRequest(
                contexts=("activity_work",),
                band_order=("normal",),
            ),
        )

        self.assertFalse(result.found)
        self.assertEqual(result.reason, "no_manifest_match")
        self.assertEqual(len(manager.calls), 1)

    def test_ignore_band_policy_keeps_context_filter_and_omits_mood_score(self):
        manager = FakeAssetManager(
            {
                ("activity_work_rest", None): (
                    ["tired-frame"],
                    "idle",
                    "manifest_tired",
                    "exhausted",
                )
            }
        )

        result = ManifestAnimationResolver().resolve(
            manager,
            ManifestAnimationRequest(
                contexts=("activity_work_rest",),
                band_policy=BAND_POLICY_IGNORE,
            ),
        )

        self.assertTrue(result.found)
        self.assertEqual(result.selection.context, "activity_work_rest")
        self.assertEqual(result.selection.band_policy, BAND_POLICY_IGNORE)
        self.assertIsNone(result.selection.band)
        self.assertEqual(manager.calls[0]["mood_score"], None)

    def test_apply_uses_resolved_selection_and_reports_pet_rejection(self):
        manager = FakeAssetManager(
            {
                ("activity_work", 60.0): (
                    ["frame"],
                    "idle",
                    "manifest_action",
                    "happy",
                )
            }
        )
        pet = FakePet(manager, apply_result=False)
        request = ManifestAnimationRequest(
            contexts=("activity_work",),
            band_order=("normal",),
        )

        result = ManifestAnimationResolver().apply(pet, request)

        self.assertFalse(result.applied)
        self.assertEqual(result.reason, "animation_apply_rejected")
        self.assertEqual(
            pet.apply_calls,
            [("idle", (["frame"], "manifest_action", "happy"))],
        )

    def test_apply_reports_missing_pet_or_asset_manager(self):
        resolver = ManifestAnimationResolver()
        request = ManifestAnimationRequest(
            contexts=("activity_work",),
            band_order=("normal",),
        )

        self.assertEqual(resolver.apply(None, request).reason, "missing_pet")
        self.assertEqual(
            resolver.apply(FakePet(asset_manager=None), request).reason,
            "missing_asset_manager",
        )


if __name__ == "__main__":
    unittest.main()
