import unittest

from tanuki_core.asset_selection_rules import (
    get_mood_band,
    get_mood_rules,
    is_record_eligible,
    select_contextual_result,
    select_contextual_result_for_candidates,
    select_contextual_result_for_purposes,
    select_result_by_score,
    select_result_for_preferences,
    select_safe_result,
)


class FirstChoiceRng:
    def choice(self, population):
        return population[0]

    def choices(self, population, weights=None, k=1):
        return [population[0]]

    def shuffle(self, population):
        return None


class RecordingChoiceRng(FirstChoiceRng):
    def __init__(self, choice_index):
        self.choice_index = choice_index
        self.weights = None

    def choices(self, population, weights=None, k=1):
        self.weights = list(weights or ())
        return [population[self.choice_index]]


def make_record(action_type, mood_tag, *, bands=None, contexts=None, weight=1.0):
    return {
        "frames": [f"{action_type}:{mood_tag}"],
        "manifest": {
            "band": list(bands or []),
            "contexts": list(contexts or []),
            "weight": weight,
        },
    }


class AssetSelectionRuleTests(unittest.TestCase):
    def test_get_mood_band_maps_score_ranges(self):
        self.assertEqual(get_mood_band(10), "severe")
        self.assertEqual(get_mood_band(30), "low")
        self.assertEqual(get_mood_band(70), "normal")

    def test_is_record_eligible_respects_band_and_context(self):
        record = make_record("sit", "happy", bands=["normal"], contexts=["random"])

        self.assertTrue(is_record_eligible(record, mood_score=60, context="random"))
        self.assertFalse(is_record_eligible(record, mood_score=30, context="random"))
        self.assertFalse(is_record_eligible(record, mood_score=60, context="care"))

    def test_is_record_eligible_accepts_multiple_context_candidates(self):
        record = make_record("sit", "happy", bands=["normal"], contexts=["random"])

        self.assertTrue(is_record_eligible(record, mood_score=60, context=["relation_watch", "random"]))
        self.assertFalse(is_record_eligible(record, mood_score=60, context=["relation_watch", "care"]))

    def test_is_record_eligible_blocks_future_only_context_without_explicit_match(self):
        record = make_record("work", "happy", bands=["severe"], contexts=["future_work"])

        self.assertFalse(is_record_eligible(record, mood_score=10))
        self.assertFalse(is_record_eligible(record, mood_score=10, context="random"))
        self.assertTrue(is_record_eligible(record, mood_score=10, context="future_work"))

    def test_is_record_eligible_blocks_disabled_context(self):
        record = make_record("stand", "happy", bands=["normal"], contexts=["disabled"])

        self.assertFalse(is_record_eligible(record, mood_score=80))
        self.assertFalse(is_record_eligible(record, mood_score=80, context="random"))

    def test_get_mood_rules_preserves_existing_adult_and_child_chains(self):
        child_priority, child_fallback, child_forbidden = get_mood_rules(10, is_adult=False)
        adult_priority, adult_fallback, adult_forbidden = get_mood_rules(10, is_adult=True)

        self.assertIn("hard-cry", child_priority)
        self.assertIn("sad", adult_priority)
        self.assertIn("happy", child_forbidden)
        self.assertIn("cool", adult_forbidden)

    def test_select_result_by_score_prefers_action_specific_mood_match(self):
        available_types = {
            "sit": {
                "happy": ["sit-happy"],
                "sad": ["sit-sad"],
            },
            "stand": {
                "happy": ["stand-happy"],
            },
        }
        records = {
            ("sit", "happy"): make_record("sit", "happy", bands=["normal"], contexts=["random"], weight=1.0),
            ("sit", "sad"): make_record("sit", "sad", bands=["low"], contexts=["random"], weight=1.0),
            ("stand", "happy"): make_record("stand", "happy", bands=["normal"], contexts=["random"], weight=1.0),
        }

        result = select_result_by_score(
            available_types,
            get_record=lambda action_type, mood_tag: records.get((action_type, mood_tag)),
            action_type="sit",
            mood_score=30,
            is_adult=False,
            context="random",
            manifest_present=True,
            rng=FirstChoiceRng(),
        )

        self.assertEqual(result, (["sit:sad"], "sit", "sad"))

    def test_select_result_by_score_falls_back_to_normal_safe_result(self):
        available_types = {
            "sit": {
                "normal": ["sit-normal"],
                "happy": ["sit-happy"],
            },
        }
        records = {
            ("sit", "normal"): make_record("sit", "normal", contexts=["random"], weight=1.0),
            ("sit", "happy"): make_record("sit", "happy", contexts=["random"], weight=1.0),
        }

        result = select_result_by_score(
            available_types,
            get_record=lambda action_type, mood_tag: records.get((action_type, mood_tag)),
            action_type="sit",
            mood_score=10,
            is_adult=False,
            context="random",
            manifest_present=True,
            rng=FirstChoiceRng(),
        )

        self.assertEqual(result, (["sit:normal"], "sit", "normal"))

    def test_select_result_for_preferences_prefers_requested_mood_then_normal(self):
        available_types = {
            "sit": {
                "happy": ["sit-happy"],
                "normal": ["sit-normal"],
            },
        }
        records = {
            ("sit", "happy"): make_record("sit", "happy", contexts=["random"], weight=1.0),
            ("sit", "normal"): make_record("sit", "normal", contexts=["random"], weight=1.0),
        }

        preferred = select_result_for_preferences(
            available_types,
            "sit",
            ["happy"],
            get_record=lambda action_type, mood_tag: records.get((action_type, mood_tag)),
            mood_score=60,
            context="random",
            rng=FirstChoiceRng(),
        )
        fallback = select_result_for_preferences(
            available_types,
            "sit",
            ["sad"],
            get_record=lambda action_type, mood_tag: records.get((action_type, mood_tag)),
            mood_score=60,
            context="random",
            rng=FirstChoiceRng(),
        )

        self.assertEqual(preferred, (["sit:happy"], "sit", "happy"))
        self.assertEqual(fallback, (["sit:normal"], "sit", "normal"))

    def test_select_contextual_result_prefers_requested_mood_with_context_filter(self):
        asset_records = {
            "sit": {
                "happy": make_record("sit", "happy", contexts=["random"], weight=1.0),
                "sad": make_record("sit", "sad", contexts=["care"], weight=1.0),
            },
            "stand": {
                "normal": make_record("stand", "normal", contexts=["random"], weight=1.0),
            },
        }

        result = select_contextual_result(
            asset_records,
            context="random",
            preferred_moods=["happy"],
            rng=FirstChoiceRng(),
        )

        self.assertEqual(result, (["sit:happy"], "sit", "happy"))

    def test_select_contextual_result_respects_mood_score_when_provided(self):
        asset_records = {
            "drag_original": {
                "sad": make_record("drag_original", "sad", bands=["low"], contexts=["drag"], weight=1.0),
                "happy": make_record("drag_original", "happy", bands=["normal"], contexts=["drag"], weight=1.0),
            },
        }

        result = select_contextual_result(
            asset_records,
            context="drag",
            preferred_moods=["sad", "happy"],
            mood_score=80,
            rng=FirstChoiceRng(),
        )

        self.assertEqual(result, (["drag_original:happy"], "drag_original", "happy"))

    def test_select_contextual_result_respects_forbidden_moods_when_band_is_ignored(self):
        asset_records = {
            "photo": {
                "happy": make_record("photo", "happy", bands=["normal"], contexts=["relation_watch"]),
                "sad": make_record("photo", "sad", bands=["low"], contexts=["relation_watch"]),
            },
        }

        result = select_contextual_result(
            asset_records,
            context="relation_watch",
            preferred_moods=["sad", "happy"],
            forbidden=["happy"],
            mood_score=None,
            ordered_preferences=True,
            rng=FirstChoiceRng(),
        )

        self.assertEqual(result, (["photo:sad"], "photo", "sad"))

    def test_select_contextual_result_can_respect_preferred_mood_order(self):
        asset_records = {
            "get": {
                "happy": make_record("get", "happy", contexts=["offer_preview"]),
                "sad": make_record("get", "sad", contexts=["offer_preview"]),
            },
        }

        result = select_contextual_result(
            asset_records,
            context="offer_preview",
            preferred_moods=["sad", "happy"],
            ordered_preferences=True,
            rng=FirstChoiceRng(),
        )

        self.assertEqual(result, (["get:sad"], "get", "sad"))

    def test_select_contextual_result_skips_records_without_frames(self):
        asset_records = {
            "get": {
                "sad": {
                    "frames": [],
                    "manifest": {"contexts": ["offer_preview"], "weight": 1.0},
                },
                "happy": make_record("get", "happy", contexts=["offer_preview"]),
            },
        }

        result = select_contextual_result(
            asset_records,
            context="offer_preview",
            preferred_moods=["sad"],
            rng=FirstChoiceRng(),
        )

        self.assertEqual(result, (["get:happy"], "get", "happy"))

    def test_select_contextual_result_for_purposes_reports_selected_purpose(self):
        asset_records = {
            "idle": {
                "side_hug": {
                    "happy": make_record("side_hug", "happy", contexts=["post_observe"], weight=0.0),
                },
            },
            "move": {
                "walk_shake": {
                    "sad": make_record("walk_shake", "sad", contexts=["post_observe"], weight=1.0),
                },
            },
        }

        result = select_contextual_result_for_purposes(
            asset_records,
            ("idle", "move"),
            context="post_observe",
            preferred_moods=["sad", "happy"],
            ordered_preferences=True,
            rng=FirstChoiceRng(),
        )

        self.assertEqual(result, (["walk_shake:sad"], "move", "walk_shake", "sad"))

    def test_candidate_pool_weights_moods_instead_of_prioritizing_happy(self):
        asset_records = {
            "move": {
                "fly": {
                    "happy": make_record(
                        "fly",
                        "happy",
                        bands=["normal"],
                        contexts=["random"],
                        weight=1.0,
                    ),
                    "smile": make_record(
                        "fly",
                        "smile",
                        bands=["normal"],
                        contexts=["random"],
                        weight=3.0,
                    ),
                },
                "activity_only": {
                    "happy": make_record(
                        "activity_only",
                        "happy",
                        bands=["normal"],
                        contexts=["activity_chorus_approach"],
                        weight=20.0,
                    ),
                },
            },
        }
        rng = RecordingChoiceRng(choice_index=1)

        result = select_contextual_result_for_candidates(
            asset_records,
            (("move", "fly"),),
            context="random",
            mood_score=80,
            rng=rng,
        )

        self.assertEqual(result, (["fly:smile"], "move", "fly", "smile"))
        self.assertEqual(rng.weights, [1.0, 3.0])

    def test_select_safe_result_prefers_requested_mood_then_safe_normal(self):
        available_types = {
            "sit": {
                "sad": ["sit-sad"],
                "normal": ["sit-normal"],
            },
            "stand": {
                "happy": ["stand-happy"],
            },
        }
        records = {
            ("sit", "sad"): make_record("sit", "sad"),
            ("sit", "normal"): make_record("sit", "normal"),
            ("stand", "happy"): make_record("stand", "happy"),
        }

        preferred = select_safe_result(
            available_types,
            ["sad"],
            get_record=lambda action_type, mood_tag: records.get((action_type, mood_tag)),
            forbidden=["happy"],
            rng=FirstChoiceRng(),
        )
        fallback = select_safe_result(
            available_types,
            ["cry"],
            get_record=lambda action_type, mood_tag: records.get((action_type, mood_tag)),
            forbidden=["happy"],
            rng=FirstChoiceRng(),
        )

        self.assertEqual(preferred, (["sit:sad"], "sit", "sad"))
        self.assertEqual(fallback, (["sit:normal"], "sit", "normal"))


if __name__ == "__main__":
    unittest.main()
