import unittest
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

try:
    from tanuki_core.item_scene_coordinator import SharedFoodSceneState
    from tanuki_core.shared_food_partner_rules import SharedFoodPartnerEligibility
    from tanuki_core.shared_food_profiles import SharedFoodCharacterCapabilities
    from tanuki_core.shared_food_scene_executor import SharedFoodSceneExecutor
except (ImportError, ModuleNotFoundError) as exc:
    SharedFoodSceneExecutor = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


@unittest.skipIf(SharedFoodSceneExecutor is None, f"runtime imports unavailable: {IMPORT_ERROR}")
class SharedFoodSceneExecutorTests(unittest.TestCase):
    def setUp(self):
        self.executor = SharedFoodSceneExecutor()

    def test_eligibility_reports_missing_participant_before_distance_checks(self):
        runtime = SimpleNamespace(build_shared_food_participant_state=Mock())

        result = self.executor.evaluate_runtime_shared_food_partner(
            runtime,
            profile=SimpleNamespace(join_distance=500.0),
            holder_pet=SimpleNamespace(name="Symboli Rudolf"),
            partner_pet=None,
            now=10.0,
        )

        self.assertFalse(result.eligible)
        self.assertEqual(result.reason, "missing_participant")
        runtime.build_shared_food_participant_state.assert_not_called()

    @patch(
        "tanuki_core.shared_food_scene_executor.preflight_shared_food_outcomes",
        return_value=("share_both", "holder_keeps"),
    )
    def test_start_scene_delegates_single_state_and_two_participant_lock(self, _preflight):
        holder_pet = SimpleNamespace(name="Symboli Rudolf", held_item_kind="ramen")
        partner_pet = SimpleNamespace(name="Tokai Teio")
        profile = SimpleNamespace(
            profile_key="ramen_rudolf_teio",
            item_kind="ramen",
            holder_preferred_moods=("happy",),
            partner_preferred_moods=("happy",),
            partner_names_for_holder=lambda _name: (partner_pet.name,),
        )
        coordinator = Mock()
        coordinator.start_scene.return_value = SimpleNamespace(started=True)
        runtime = SimpleNamespace(
            offer_scene=None,
            evaluate_runtime_shared_food_partner=Mock(
                return_value=SharedFoodPartnerEligibility(True, "eligible", 120.0)
            ),
            pet_is_window_transitioning_for_offer=Mock(return_value=False),
            prepare_pet_window_state_for_offer=Mock(return_value=False),
            build_runtime_shared_food_capabilities=Mock(
                return_value=SharedFoodCharacterCapabilities(
                    hold_candidates=(("idle", "hold"),),
                    approach_candidates=(("move", "walk"),),
                    consume_candidates=(("idle", "eat"),),
                    request_candidates=(("idle", "request"),),
                    watch_candidates=(("idle", "watch"),),
                    react_candidates=(("idle", "react"),),
                )
            ),
            ensure_pet_held_item=Mock(return_value=object()),
            interrupt_pet_window_motion_for_offer=Mock(),
            get_shared_food_approach_timeout=Mock(return_value=3.0),
            item_scene_coordinator=coordinator,
            clear_pet_held_item=Mock(),
            update_shared_food_scene=Mock(return_value=True),
        )

        result = self.executor.start_shared_food_scene(
            runtime,
            holder_pet,
            partner_pet,
            profile=profile,
            source="ground",
            outcome_roll=0.25,
            now=10.0,
        )

        self.assertTrue(result)
        call = coordinator.start_scene.call_args
        self.assertIs(call.args[0], runtime)
        self.assertEqual(call.kwargs["participant_pets"], (holder_pet, partner_pet))
        self.assertEqual(call.kwargs["scene_kind"], "shared_food")
        self.assertEqual(call.kwargs["stage"], "partner_approach")
        self.assertEqual(call.kwargs["stage_started_at"], 10.0)
        self.assertEqual(call.kwargs["stage_ends_at"], 13.0)
        shared_state = call.kwargs["shared_food_state"]
        self.assertEqual(shared_state.available_outcomes, ("share_both", "holder_keeps"))
        self.assertEqual(shared_state.outcome_roll, 0.25)
        self.assertFalse(shared_state.outcome_resolved)
        runtime.update_shared_food_scene.assert_called_once_with(10.0)

    @patch("tanuki_core.shared_food_scene_executor.get_shared_food_profile")
    def test_update_falls_back_to_solo_when_partner_becomes_busy_before_consume(
        self,
        get_profile,
    ):
        holder_pet = SimpleNamespace(name="Symboli Rudolf", isVisible=Mock(return_value=True))
        partner_pet = SimpleNamespace(name="Tokai Teio", isVisible=Mock(return_value=True))
        shared_state = SharedFoodSceneState(
            holder_name=holder_pet.name,
            partner_name=partner_pet.name,
        )
        scene = SimpleNamespace(
            scene_kind="shared_food",
            profile_key="ramen_rudolf_teio",
            item_kind="ramen",
            actor_name=holder_pet.name,
            target_name=partner_pet.name,
            stage="partner_approach",
            shared_food_state=shared_state,
        )
        get_profile.return_value = SimpleNamespace(item_kind="ramen")
        runtime = SimpleNamespace(
            offer_scene=scene,
            find_pet_by_name=Mock(side_effect=lambda name, visible_only=False: {
                holder_pet.name: holder_pet,
                partner_pet.name: partner_pet,
            }.get(name)),
            pet_is_unavailable_during_shared_food=Mock(side_effect=(False, True)),
            fallback_shared_food_to_solo=Mock(return_value=True),
            clear_offer_scene=Mock(),
        )

        result = self.executor.update_shared_food_scene(runtime, now=10.5)

        self.assertTrue(result)
        runtime.fallback_shared_food_to_solo.assert_called_once_with(holder_pet)
        runtime.clear_offer_scene.assert_not_called()

    def test_outcome_effects_reward_consumers_and_holder_give_only_once(self):
        shared_state = SharedFoodSceneState(
            holder_name="Sirius Symboli",
            partner_name="Tokai Teio",
            outcome_key="holder_gives",
            consumer_names=("Tokai Teio",),
        )
        runtime = SimpleNamespace(apply_offer_mood_reward=Mock(return_value=True))

        first_result = self.executor.apply_shared_food_outcome_effects(runtime, shared_state)
        second_result = self.executor.apply_shared_food_outcome_effects(runtime, shared_state)

        self.assertTrue(first_result)
        self.assertFalse(second_result)
        self.assertEqual(
            runtime.apply_offer_mood_reward.call_args_list,
            [
                call("Tokai Teio", amount=6.0),
                call("Sirius Symboli", amount=2.0),
            ],
        )

    def test_set_stage_mutates_one_active_scene_state(self):
        scene = SimpleNamespace(
            scene_kind="shared_food",
            stage="partner_approach",
            stage_initialized=True,
            stage_started_at=1.0,
            stage_ends_at=2.0,
            scene_ends_at=2.0,
        )
        runtime = SimpleNamespace(offer_scene=scene)

        result = self.executor.set_shared_food_stage(
            runtime,
            "request_decision",
            now=10.0,
            duration=1.2,
        )

        self.assertTrue(result)
        self.assertEqual(scene.stage, "request_decision")
        self.assertFalse(scene.stage_initialized)
        self.assertEqual(scene.stage_started_at, 10.0)
        self.assertEqual(scene.stage_ends_at, 11.2)
        self.assertEqual(scene.scene_ends_at, 11.2)


if __name__ == "__main__":
    unittest.main()
