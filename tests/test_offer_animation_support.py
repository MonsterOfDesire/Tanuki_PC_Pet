import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from tanuki_core.offer_animation_support import OfferAnimationSupport


class OfferAnimationSupportTests(unittest.TestCase):
    def build_support(self, *, pets=()):
        return OfferAnimationSupport(
            pets=list(pets),
            pet_registry=SimpleNamespace(find_by_name=Mock(return_value=None)),
            lock_pet_for_offer_scene=Mock(),
            held_item_position_updater=Mock(),
            now_provider=lambda: 12.0,
        )

    def test_pending_drag_press_blocks_offer_interaction(self):
        pet = SimpleNamespace(
            transformation_state=None,
            activity_state=None,
            intent_kind="none",
            dragging=False,
            drag_press_pending=True,
            flight_mode="none",
            care_mode="none",
            care_partner=None,
            is_hugging=False,
            is_under_care=lambda now: False,
        )

        self.assertTrue(
            self.build_support().pet_is_busy_for_offer_interaction(pet)
        )

    def test_scene_context_delegates_manifest_selection_to_pet(self):
        changer = Mock(return_value=True)
        pet = SimpleNamespace(
            change_state_for_context_with_preferences=changer,
        )

        applied = self.build_support().apply_scene_context_with_preferences(
            pet,
            "idle",
            "offer_preview",
            preferred_moods=("happy",),
            forbidden=("sad",),
            preserve=True,
        )

        self.assertTrue(applied)
        changer.assert_called_once_with(
            "idle",
            "offer_preview",
            preferred_moods=("happy",),
            forbidden=("sad",),
            preserve=True,
            ignore_mood_band=False,
        )

    def test_held_item_uses_injected_lock_and_position_callbacks(self):
        support = self.build_support()
        support.apply_scene_context_with_preferences = Mock(return_value=True)
        widget = object()
        pet = SimpleNamespace(
            name="Sirius Symboli",
            held_item_kind="bottle",
            held_item_widget=widget,
            state="move",
            perception_situation_tag="",
            expression_animation_context="",
            expression_relation_overlay="",
            expression_focus_target_name="",
            expression_posture_bias="",
            expression_spacing_bias="",
            expression_look_at_target=True,
            relationship_focus_target_name="target",
            refresh_movement_state=Mock(),
            ensure_candidate_animation_with_preferences=Mock(),
            ensure_candidate_animation=Mock(),
        )

        self.assertTrue(support.apply_held_item_behavior(pet, 20.0))

        support.lock_pet_for_offer_scene.assert_called_once_with(
            pet,
            "held_item",
            20.2,
        )
        support.held_item_position_updater.assert_called_once_with(
            widget,
            pet,
            "bottle",
            prefer_preview=True,
        )

    def test_scene_context_can_explicitly_preserve_semantic_mood_order(self):
        changer = Mock(return_value=True)
        pet = SimpleNamespace(
            change_state_for_context_with_preferences=changer,
        )

        applied = self.build_support().apply_scene_context_with_preferences(
            pet,
            "idle",
            "offer_denied",
            preferred_moods=("hard-cry", "cry", "sad"),
            ignore_mood_band=True,
            ordered_preferences=True,
        )

        self.assertTrue(applied)
        self.assertTrue(
            changer.call_args.kwargs["ordered_preferences"]
        )

    def test_scene_candidate_pool_weights_all_allowed_moods_when_unordered(self):
        class AssetManager:
            def __init__(self):
                self.received = []

            def get_record(self, purpose, action_type, mood_tag):
                if (purpose, action_type, mood_tag) not in {
                    ("move", "climb", "happy"),
                    ("move", "climb", "smile"),
                }:
                    return None
                return {
                    "frames": [mood_tag],
                    "manifest": {
                        "weight": 1.0 if mood_tag == "happy" else 3.0,
                    },
                }

            def get_record_weight(self, record):
                return record["manifest"]["weight"]

            def choose_weighted_result(self, results):
                self.received = list(results)
                return results[-1][0], results[-1][1], results[-1][2]

            def get_frames_for_action_by_preferences(self, *args, **kwargs):
                return None

        manager = AssetManager()
        pet = SimpleNamespace(
            asset_manager=manager,
            current_mood_tag="happy",
            current_purpose="idle",
            current_action_tag="stand",
            state="idle",
            apply_animation_result=Mock(return_value=True),
        )

        applied = self.build_support().apply_scene_candidates_with_preferences(
            pet,
            [("move", "climb")],
            ["happy", "smile"],
            ordered_preferences=False,
        )

        self.assertTrue(applied)
        self.assertEqual(
            [result[3] for result in manager.received],
            [1.0, 3.0],
        )
        pet.apply_animation_result.assert_called_once_with(
            "move",
            (["smile"], "climb", "smile"),
        )


if __name__ == "__main__":
    unittest.main()
