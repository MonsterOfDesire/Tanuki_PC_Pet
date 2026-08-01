import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from tanuki_core.asset_loader import AssetStoreCache, FrameCache
from tanuki_core.asset_manager import AssetManager
from tanuki_core.pet_basics import PetBasicsMixin
from tanuki_core.pet_social_care import PetSocialCareMixin


ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets_cropped"


class TransformationAssetIntegrationTests(unittest.TestCase):
    def build_manager(self, character_name, *, transformed=True):
        path = ASSETS_DIR / character_name
        if transformed:
            path /= "transformed"

        def fake_extract(gif_path, scale_factor, frame_cache=None):
            return [f"{os.path.basename(gif_path)}@{scale_factor}"]

        with patch(
            "tanuki_core.asset_manager.extract_frames",
            side_effect=fake_extract,
        ):
            return AssetManager(
                str(path),
                scale_factor=1.0,
                frame_cache=FrameCache(),
                store_cache=AssetStoreCache(),
            )

    def test_every_runtime_form_resolves_hard_landing_context(self):
        forms = (
            ("Air Groove", False),
            ("Sirius Symboli", False),
            ("Symboli Rudolf", False),
            ("Tokai Teio", False),
            ("Tsurumaru Tsuyoshi", False),
            ("Symboli Rudolf", True),
            ("Tokai Teio", True),
        )
        for character_name, transformed in forms:
            manager = self.build_manager(
                character_name,
                transformed=transformed,
            )

            result = manager.get_contextual_result_for_any_purpose(
                context="hard_landing",
                mood_score=60.0,
                ordered_preferences=True,
            )
            if result is None:
                result = manager.get_contextual_result_for_any_purpose(
                    context="hard_landing",
                    mood_score=None,
                    ordered_preferences=True,
                )

            self.assertIsNotNone(
                result,
                f"{character_name} transformed={transformed}",
            )

    def test_transformed_teio_drag_context_resolves_move_purpose(self):
        manager = self.build_manager("Tokai Teio")

        result = manager.get_contextual_result_for_any_purpose(
            context="drag",
            mood_score=60.0,
        )

        self.assertIsNotNone(result)
        self.assertEqual(result[1], "move")
        self.assertIn(result[3], {"cute", "happy", "serious", "smile"})

    def test_both_transformed_forms_have_random_swap_entry(self):
        for character_name in ("Tokai Teio", "Symboli Rudolf"):
            manager = self.build_manager(character_name)

            result = manager.get_contextual_result_for_any_purpose(
                context="random",
                mood_score=50.0,
                ordered_preferences=True,
            )

            self.assertIsNotNone(result, character_name)

    def test_drag_animation_falls_back_to_context_across_purposes(self):
        class DragPet(PetBasicsMixin, PetSocialCareMixin):
            def __init__(self, manager):
                self.asset_manager = manager
                self.mood_score = 60.0
                self.is_adult = False
                self.state = "idle"
                self.applied_purposes = []

            def apply_animation_result(self, purpose, result):
                if not result:
                    return False
                self.applied_purposes.append(purpose)
                return True

        pet = DragPet(self.build_manager("Tokai Teio"))

        applied = pet.apply_drag_animation()

        self.assertTrue(applied)
        self.assertEqual(pet.applied_purposes, ["move"])

    def test_transformed_rudolf_drag_keeps_drag_purpose(self):
        manager = self.build_manager("Symboli Rudolf")

        result = manager.get_contextual_result_for_any_purpose(
            context="drag",
            mood_score=60.0,
        )

        self.assertIsNotNone(result)
        self.assertEqual(result[1], "drag")

    def test_transformed_manifests_exclude_blocked_runtime_contexts(self):
        forbidden_context_prefixes = (
            "activity_sleep",
            "activity_work",
            "shared_food",
            "offer_accept",
            "social_follow",
            "social_mimic",
            "care_interaction",
            "moving_care_interaction",
        )
        for character_name in ("Tokai Teio", "Symboli Rudolf"):
            manifest_path = (
                ASSETS_DIR
                / character_name
                / "transformed"
                / "manifest_edit.json"
            )
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            for file_name, metadata in payload["animations"].items():
                for context in metadata.get("contexts", ()):
                    self.assertFalse(
                        context.startswith(forbidden_context_prefixes),
                        f"{character_name}/{file_name}: {context}",
                    )
                self.assertEqual(metadata.get("band"), ["normal"])


if __name__ == "__main__":
    unittest.main()
