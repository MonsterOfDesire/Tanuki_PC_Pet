import unittest
from unittest.mock import patch

from tanuki_core.asset_selection_rules import (
    is_record_eligible,
    select_contextual_result_for_candidates,
)
from tanuki_core.pet_social_care import PetSocialCareMixin
from tests.test_pet_widget_runtime import FakePetForRandomManifest, TanukiPet


class AfterglowAssetManager:
    """Use the real manifest selector with distinct band/context candidates."""

    def __init__(self):
        self.asset_records = {}
        for purpose in ("idle", "move"):
            self.asset_records[purpose] = {
                "happy_only": {"happy": self.record("normal", "random", 100.0)},
                "sad_only": {"sad": self.record("low", "random")},
                "cry_only": {"cry": self.record("severe", "random")},
                "scene_only": {"sad": self.record("low", "offer_denied", 1000.0)},
            }

    @staticmethod
    def record(band, context, weight=1.0):
        return {"frames": [context], "manifest": {
            "band": [band], "contexts": [context], "weight": weight,
        }}

    def get_action_keys_for_context(self, purpose, mood_score=None, context=None):
        return [
            action for action, moods in self.asset_records[purpose].items()
            if any(is_record_eligible(record, mood_score=mood_score, context=context)
                   for record in moods.values())
        ]

    def get_specific_frames(self, purpose, action_type, mood_tag, mood_score=None, context=None):
        record = self.asset_records.get(purpose, {}).get(action_type, {}).get(mood_tag)
        if record and is_record_eligible(record, mood_score=mood_score, context=context):
            return record["frames"]
        return None

    def get_contextual_result_for_candidates(self, candidates, **kwargs):
        return select_contextual_result_for_candidates(self.asset_records, candidates, **kwargs)


class AfterglowPet(FakePetForRandomManifest, PetSocialCareMixin):
    SEVERE_MOODS = TanukiPet.SEVERE_MOODS
    apply_animation_result = PetSocialCareMixin.apply_animation_result
    change_state_candidates = PetSocialCareMixin.change_state_candidates
    should_apply_negative_afterglow_to_candidates = (
        PetSocialCareMixin.should_apply_negative_afterglow_to_candidates
    )
    apply_random_idle_animation = TanukiPet.apply_random_idle_animation
    reset_stationary_move_mode = PetSocialCareMixin.reset_stationary_move_mode

    def __init__(self, purpose, mood_score):
        super().__init__()
        self.name = "Tsurumaru Tsuyoshi"
        self.is_adult = False
        self.state = purpose
        self.social_mode = self.care_mode = self.offer_scene_kind = "none"
        self.current_purpose = purpose
        self.current_action_tag = "happy_only"
        self.current_mood_tag = "happy"
        self.current_frames = ["random"]
        self.mood_score = mood_score
        self.asset_manager = AfterglowAssetManager()
        self.start_negative_afterglow(
            duration=5.0, now=10.0, preferred_moods=("cry", "sad"),
            forbidden_moods=("happy", "smile"), block_care=True,
        )

    def is_under_care(self, now):
        return False

    def apply_expression_idle_behavior(self, context):
        return False


class HoneyAfterglowRuntimeTests(unittest.TestCase):
    def test_free_idle_and_move_retain_negative_afterglow_in_all_mood_bands(self):
        for purpose in ("idle", "move"):
            for mood_score in (70.0, 35.0, 10.0):
                with self.subTest(purpose=purpose, mood_score=mood_score):
                    pet = AfterglowPet(purpose, mood_score)
                    for now in (12.0, 13.0, 14.99):
                        with (
                            patch("tanuki_core.pet_social_care.app_now", return_value=now),
                            patch("tanuki_core.pet_widget.app_now", return_value=now),
                        ):
                            TanukiPet.update_random_behavior(pet)
                        self.assertIn(pet.current_mood_tag, ("cry", "sad"))
                        self.assertNotEqual(pet.current_action_tag, "scene_only")
                        self.assertEqual(pet.offer_scene_kind, "none")
                        self.assertEqual(pet.negative_afterglow_until, 15.0)
                        self.assertEqual(pet.mood_score, mood_score)
                    if purpose == "move" and mood_score >= 20:
                        self.assertEqual(pet.moved, 3)

    def test_afterglow_expiry_restores_normal_band_random_pool(self):
        for purpose in ("idle", "move"):
            with self.subTest(purpose=purpose):
                pet = AfterglowPet(purpose, 70.0)
                with patch("tanuki_core.pet_social_care.app_now", return_value=14.99):
                    TanukiPet.update_random_behavior(pet)
                    self.assertIn(pet.current_mood_tag, ("cry", "sad"))
                with patch("tanuki_core.pet_social_care.app_now", return_value=15.0):
                    TanukiPet.update_random_behavior(pet)
                    self.assertEqual(pet.current_mood_tag, "happy")
                    self.assertFalse(pet.is_negative_afterglow_active())


if __name__ == "__main__":
    unittest.main()
