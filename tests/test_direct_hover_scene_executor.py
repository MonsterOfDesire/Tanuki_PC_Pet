import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

try:
    from tanuki_core.direct_hover_scene_executor import DirectHoverSceneExecutor
except (ImportError, ModuleNotFoundError) as exc:
    DirectHoverSceneExecutor = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


@unittest.skipIf(DirectHoverSceneExecutor is None, f"runtime imports unavailable: {IMPORT_ERROR}")
class DirectHoverSceneExecutorTests(unittest.TestCase):
    def setUp(self):
        self.executor = DirectHoverSceneExecutor()

    def test_negative_afterglow_updates_mood_and_constraints(self):
        pet = SimpleNamespace(
            mood_score=55.0,
            start_negative_afterglow=Mock(),
            sync_mood_state_with_score=Mock(),
        )

        result = self.executor.apply_offer_negative_afterglow(
            SimpleNamespace(),
            pet,
            now=20.0,
            amount=15.0,
            duration=4.0,
        )

        self.assertTrue(result)
        self.assertEqual(pet.mood_score, 40.0)
        pet.start_negative_afterglow.assert_called_once_with(
            duration=4.0,
            preferred_moods=["hard-cry", "cry", "sad", "scared", "think"],
            forbidden_moods=["happy", "smile", "relief", "calm", "confidence", "cool", "glance"],
            now=20.0,
        )
        pet.sync_mood_state_with_score.assert_called_once_with()

    def test_hover_timeout_drop_routes_only_first_stage_to_interaction(self):
        target_pet = SimpleNamespace(name="Tsurumaru Tsuyoshi")
        scene = SimpleNamespace(
            scene_kind="hover_timeout_reaction",
            hover_reaction_stages=(object(), object()),
            hover_reaction_stage_index=0,
            target_name=target_pet.name,
        )
        runtime = SimpleNamespace(
            offer_scene=scene,
            find_offer_drop_target=Mock(return_value=target_pet),
            find_offer_hover_target=Mock(return_value=None),
            clear_offer_scene=Mock(),
            clear_offer_hover=Mock(),
            find_pet_by_name=Mock(return_value=target_pet),
            pet_is_busy_for_offer_interaction=Mock(return_value=False),
            start_offer_interaction_for_target=Mock(return_value=True),
        )

        result = self.executor.hover_timeout_scene_accepts_offer_drop(
            runtime,
            "ramen",
            (120, 200),
        )

        self.assertTrue(result)
        runtime.clear_offer_scene.assert_called_once_with()
        runtime.clear_offer_hover.assert_called_once_with(apply_miss=False)
        runtime.start_offer_interaction_for_target.assert_called_once_with(
            "ramen",
            target_pet,
            source="offer_tray",
        )

        scene.hover_reaction_stage_index = 1
        runtime.start_offer_interaction_for_target.reset_mock()
        self.assertFalse(
            self.executor.hover_timeout_scene_accepts_offer_drop(
                runtime,
                "ramen",
                (120, 200),
            )
        )
        runtime.start_offer_interaction_for_target.assert_not_called()

    @patch("tanuki_core.direct_hover_scene_executor.get_direct_offer_accept_purpose_order")
    def test_start_direct_scene_delegates_lock_reward_and_event(
        self,
        purpose_order,
    ):
        purpose_order.return_value = ("idle", "move")
        target_pet = SimpleNamespace(name="Symboli Rudolf")
        coordinator = Mock()
        coordinator.start_scene.return_value = SimpleNamespace(started=True)
        runtime = SimpleNamespace(
            item_scene_coordinator=coordinator,
            apply_offer_mood_reward=Mock(),
            record_offer_event=Mock(),
        )

        result = self.executor.start_direct_offer_scene(
            runtime,
            "tea",
            target_pet,
            source="ground",
            now=10.0,
            roll=0.25,
        )

        self.assertTrue(result)
        coordinator.start_scene.assert_called_once_with(
            runtime,
            participant_pets=(target_pet,),
            item_kind="tea",
            scene_kind="direct_accept",
            actor_name=target_pet.name,
            target_name=target_pet.name,
            stage="accept",
            stage_ends_at=11.8,
            scene_ends_at=11.8,
            source="ground",
            direct_accept_purpose_order=("idle", "move"),
        )
        runtime.apply_offer_mood_reward.assert_called_once_with(target_pet.name)
        runtime.record_offer_event.assert_called_once_with(
            "tea",
            target_pet.name,
            target_pet.name,
            "direct_accept",
            source="ground",
        )

    @patch("tanuki_core.direct_hover_scene_executor.get_direct_offer_accept_context", return_value="offer_accept_tea")
    @patch("tanuki_core.direct_hover_scene_executor.get_direct_offer_preferred_moods", return_value=("happy",))
    @patch("tanuki_core.direct_hover_scene_executor.get_direct_offer_accept_candidates", return_value=(("idle", "drink"),))
    def test_update_direct_scene_uses_runtime_animation_and_motion_facades(
        self,
        _candidates,
        _moods,
        _context,
    ):
        pet = SimpleNamespace(
            name="Symboli Rudolf",
            ensure_candidate_animation_with_preferences=Mock(return_value=True),
            ensure_candidate_animation=Mock(return_value=True),
            perception_situation_tag="",
            expression_animation_context="",
            expression_relation_overlay="",
            expression_focus_target_name="",
            expression_posture_bias="",
            expression_spacing_bias="",
            expression_look_at_target=True,
            relationship_focus_target_name="other",
        )
        scene = SimpleNamespace(
            target_name=pet.name,
            item_kind="tea",
            scene_ends_at=20.0,
            direct_accept_purpose_order=("idle",),
        )
        runtime = SimpleNamespace(
            offer_scene=scene,
            find_pet_by_name=Mock(return_value=pet),
            clear_offer_scene=Mock(),
            refresh_offer_scene_locks=Mock(),
            order_candidates_by_purpose=Mock(return_value=(("idle", "drink"),)),
            apply_scene_contexts_with_preferences=Mock(return_value=True),
            update_direct_offer_accept_motion=Mock(),
        )

        result = self.executor.update_direct_offer_scene(runtime, now=15.0)

        self.assertTrue(result)
        runtime.refresh_offer_scene_locks.assert_called_once_with(pet)
        runtime.apply_scene_contexts_with_preferences.assert_called_once_with(
            pet,
            ("idle",),
            "offer_accept_tea",
            ("happy",),
            preserve=True,
        )
        runtime.update_direct_offer_accept_motion.assert_called_once_with(
            pet,
            "tea",
            "offer_accept_tea",
            (("idle", "drink"),),
        )
        self.assertEqual(pet.perception_situation_tag, "locked")
        self.assertFalse(pet.expression_look_at_target)


if __name__ == "__main__":
    unittest.main()
