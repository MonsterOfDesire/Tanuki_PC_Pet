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


if __name__ == "__main__":
    unittest.main()
