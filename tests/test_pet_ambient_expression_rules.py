import json
import unittest
from pathlib import Path

from tanuki_core.pet_ambient_expression_rules import (
    advance_ambient_low_mood_streak,
    apply_ambient_low_mood_tendency,
    choose_ambient_low_mood_tag,
    get_ambient_low_same_mood_probability,
    reset_ambient_low_mood_tendency_if_inactive,
)


class StubRng:
    def __init__(self, roll=0.0, choice_index=0):
        self.roll = roll
        self.choice_index = choice_index
        self.seen_weights = None

    def random(self):
        return self.roll

    def choices(self, options, weights, k):
        self.seen_weights = list(weights)
        return [options[self.choice_index]]

    def choice(self, options):
        return options[self.choice_index]


class FakeAssetManager:
    def __init__(self, records):
        self.records = records

    def get_specific_frames(
        self,
        purpose,
        action_type,
        mood_tag,
        mood_score=None,
        context=None,
    ):
        record = self.get_record(purpose, action_type, mood_tag)
        if not record or context not in record["manifest"]["contexts"]:
            return None
        if "low" not in record["manifest"]["band"]:
            return None
        return record["frames"]

    def get_record(self, purpose, action_type, mood_tag):
        return self.records.get((purpose, action_type, mood_tag))


class FakePet:
    def __init__(self, records, *, mood_score=40.0):
        self.mood_score = mood_score
        self.ambient_low_mood_tag = ""
        self.ambient_low_mood_streak = 0
        self.current_mood_tag = ""
        self.asset_manager = FakeAssetManager(records)
        self.default_calls = []
        self.afterglow = False

    def should_apply_negative_afterglow_to_candidates(self, candidates):
        return self.afterglow

    def change_state_candidates(self, candidates, context=None):
        self.default_calls.append((tuple(candidates), context))
        self.current_mood_tag = "angry"
        return True

    def apply_animation_result(self, purpose, result):
        _frames, _action_type, mood_tag = result
        self.current_mood_tag = mood_tag
        return True


def build_record(frame, *, weight=1.0, contexts=("random",), bands=("low",)):
    return {
        "frames": [frame],
        "manifest": {
            "weight": weight,
            "contexts": list(contexts),
            "band": list(bands),
        },
    }


class PetAmbientExpressionRulesTests(unittest.TestCase):
    def test_tsuyoshi_scared_random_asset_is_severe_only(self):
        manifest_path = (
            Path(__file__).resolve().parents[1]
            / "assets_cropped"
            / "Tsurumaru Tsuyoshi"
            / "manifest_edit.json"
        )
        animations = json.loads(
            manifest_path.read_text(encoding="utf-8")
        )["animations"]

        self.assertEqual(
            animations["idle_side-scared.gif"]["band"],
            ["severe"],
        )

    def test_same_mood_probability_decays_by_five_percent_to_floor(self):
        self.assertAlmostEqual(get_ambient_low_same_mood_probability(1), 0.95)
        self.assertAlmostEqual(get_ambient_low_same_mood_probability(2), 0.90)
        self.assertAlmostEqual(get_ambient_low_same_mood_probability(3), 0.85)
        self.assertAlmostEqual(get_ambient_low_same_mood_probability(18), 0.1)
        self.assertAlmostEqual(get_ambient_low_same_mood_probability(20), 0.1)

    def test_choice_stays_or_switches_symmetrically_from_previous_family(self):
        self.assertEqual(
            choose_ambient_low_mood_tag(
                "angry", 1, ("angry", "sad"), roll=0.94
            ),
            "angry",
        )
        self.assertEqual(
            choose_ambient_low_mood_tag(
                "angry", 1, ("angry", "sad"), roll=0.96
            ),
            "sad",
        )
        self.assertEqual(
            choose_ambient_low_mood_tag(
                "sad", 2, ("angry", "sad"), roll=0.89
            ),
            "sad",
        )
        self.assertEqual(
            choose_ambient_low_mood_tag(
                "sad", 2, ("angry", "sad"), roll=0.91
            ),
            "angry",
        )

    def test_choice_respects_available_exact_manifest_mood_tags(self):
        self.assertEqual(
            choose_ambient_low_mood_tag(
                "angry", 3, ("sad",), roll=0.0
            ),
            "sad",
        )
        self.assertIsNone(
            choose_ambient_low_mood_tag("", 0, ("angry", "sad"), roll=0.0)
        )

    def test_streak_advances_switches_and_resets(self):
        self.assertEqual(
            advance_ambient_low_mood_streak("angry", 1, "angry"),
            ("angry", 2),
        )
        self.assertEqual(
            advance_ambient_low_mood_streak("angry", 3, "sad"),
            ("sad", 1),
        )
        self.assertEqual(
            advance_ambient_low_mood_streak("sad", 2, "awkward"),
            ("", 0),
        )

    def test_apply_selects_within_chosen_family_and_preserves_manifest_weights(self):
        records = {
            ("idle", "stand", "angry"): build_record("angry-stand", weight=2.0),
            ("idle", "side", "angry"): build_record("angry-side", weight=7.0),
            ("idle", "stand", "sad"): build_record("sad-stand", weight=5.0),
        }
        pet = FakePet(records)
        pet.ambient_low_mood_tag = "angry"
        pet.ambient_low_mood_streak = 1
        rng = StubRng(roll=0.1, choice_index=1)

        applied = apply_ambient_low_mood_tendency(
            pet,
            (("idle", "stand"), ("idle", "side")),
            rng=rng,
        )

        self.assertTrue(applied)
        self.assertEqual(pet.current_mood_tag, "angry")
        self.assertEqual(pet.ambient_low_mood_streak, 2)
        self.assertEqual(rng.seen_weights, [2.0, 7.0])
        self.assertEqual(pet.default_calls, [])

    def test_first_low_draw_uses_existing_selector_then_starts_streak(self):
        pet = FakePet({})

        applied = apply_ambient_low_mood_tendency(
            pet,
            (("idle", "stand"),),
            rng=StubRng(),
        )

        self.assertTrue(applied)
        self.assertEqual(
            pet.default_calls,
            [((("idle", "stand"),), "random")],
        )
        self.assertEqual(pet.ambient_low_mood_tag, "angry")
        self.assertEqual(pet.ambient_low_mood_streak, 1)

    def test_negative_afterglow_bypasses_without_changing_ambient_streak(self):
        pet = FakePet({})
        pet.ambient_low_mood_tag = "sad"
        pet.ambient_low_mood_streak = 4
        pet.afterglow = True

        applied = apply_ambient_low_mood_tendency(
            pet,
            (("idle", "stand"),),
            rng=StubRng(),
        )

        self.assertTrue(applied)
        self.assertEqual(pet.ambient_low_mood_tag, "sad")
        self.assertEqual(pet.ambient_low_mood_streak, 4)

    def test_leaving_low_band_resets_runtime_tendency(self):
        pet = FakePet({}, mood_score=60.0)
        pet.ambient_low_mood_tag = "sad"
        pet.ambient_low_mood_streak = 3

        reset = reset_ambient_low_mood_tendency_if_inactive(pet)

        self.assertTrue(reset)
        self.assertEqual(pet.ambient_low_mood_tag, "")
        self.assertEqual(pet.ambient_low_mood_streak, 0)


if __name__ == "__main__":
    unittest.main()
