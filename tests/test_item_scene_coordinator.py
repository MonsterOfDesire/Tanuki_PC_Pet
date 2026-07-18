import unittest
from types import SimpleNamespace

from tanuki_core.item_scene_coordinator import (
    ActiveItemScene,
    ItemSceneCoordinator,
    SharedFoodSceneState,
)
from tanuki_core.shared_food_profiles import (
    SHARED_FOOD_OUTCOME_DEFINITIONS_BY_KEY,
    SHARED_FOOD_OUTCOME_HOLDER_GIVES,
    SHARED_FOOD_OUTCOME_HOLDER_KEEPS,
    SHARED_FOOD_OUTCOME_SHARE_BOTH,
    get_shared_food_profile,
    get_shared_food_profile_for_item,
    get_shared_food_profile_for_holder,
    get_shared_food_partner_names,
)


class ItemSceneCoordinatorTests(unittest.TestCase):
    def test_start_scene_sets_runtime_offer_scene(self):
        runtime = SimpleNamespace(offer_scene=None)
        coordinator = ItemSceneCoordinator()
        pet = SimpleNamespace(
            name="Tsurumaru Tsuyoshi",
            offer_scene_kind="none",
            offer_locked_until=0.0,
        )

        result = coordinator.start_scene(
            runtime,
            participant_pets=(pet,),
            scene_kind="direct_accept",
            item_kind="bottle",
            actor_name="Tsurumaru Tsuyoshi",
            target_name="Tsurumaru Tsuyoshi",
            stage="accept",
            scene_ends_at=3.5,
            source="offer_tray",
        )

        self.assertTrue(result.started)
        self.assertEqual(runtime.offer_scene.scene_kind, "direct_accept")
        self.assertEqual(runtime.offer_scene.item_kind, "bottle")
        self.assertEqual(runtime.offer_scene.target_name, "Tsurumaru Tsuyoshi")
        self.assertEqual(pet.offer_scene_kind, "direct_accept")
        self.assertEqual(pet.offer_locked_until, 3.5)

    def test_start_scene_rejects_unknown_scene_kind(self):
        runtime = SimpleNamespace(offer_scene=None)
        coordinator = ItemSceneCoordinator()

        result = coordinator.start_scene(
            runtime,
            scene_kind="mystery_scene",
            item_kind="tea",
            actor_name="Symboli Rudolf",
        )

        self.assertFalse(result.started)
        self.assertEqual(result.reason, "unsupported_scene_kind")
        self.assertIsNone(runtime.offer_scene)

    def test_clear_scene_unlocks_all_participants(self):
        actor = SimpleNamespace(
            name="Symboli Rudolf",
            offer_scene_kind="shared_food",
            offer_locked_until=20.0,
        )
        target = SimpleNamespace(
            name="Air Groove",
            offer_scene_kind="shared_food",
            offer_locked_until=20.0,
        )
        pets = {
            actor.name: actor,
            target.name: target,
        }
        runtime = SimpleNamespace(
            offer_scene=ActiveItemScene(
                item_kind="tea",
                scene_kind="shared_food",
                actor_name=actor.name,
                target_name=target.name,
            )
        )
        coordinator = ItemSceneCoordinator()

        cleared = coordinator.clear_scene(
            runtime,
            find_pet_by_name=lambda name, visible_only=False: pets.get(name),
        )

        self.assertTrue(cleared)
        self.assertIsNone(runtime.offer_scene)
        self.assertEqual(actor.offer_scene_kind, "none")
        self.assertEqual(actor.offer_locked_until, 0.0)
        self.assertEqual(target.offer_scene_kind, "none")
        self.assertEqual(target.offer_locked_until, 0.0)

    def test_unlock_pet_does_not_clear_a_newer_scene_lock(self):
        pet = SimpleNamespace(
            offer_scene_kind="bottle_feed",
            offer_locked_until=30.0,
        )
        coordinator = ItemSceneCoordinator()

        unlocked = coordinator.unlock_pet(
            pet,
            expected_scene_kind="hover_preview",
        )

        self.assertFalse(unlocked)
        self.assertEqual(pet.offer_scene_kind, "bottle_feed")
        self.assertEqual(pet.offer_locked_until, 30.0)

    def test_lock_scene_participants_uses_active_scene_kind_and_deadline(self):
        pet = SimpleNamespace(
            offer_scene_kind="held_item",
            offer_locked_until=5.0,
        )
        runtime = SimpleNamespace(
            offer_scene=ActiveItemScene(
                item_kind="bottle",
                scene_kind="bottle_feed",
                actor_name="Symboli Rudolf",
                target_name="Tsurumaru Tsuyoshi",
                scene_ends_at=40.0,
            )
        )
        coordinator = ItemSceneCoordinator()

        locked_count = coordinator.lock_scene_participants(runtime, (pet, pet, None))

        self.assertEqual(locked_count, 1)
        self.assertEqual(pet.offer_scene_kind, "bottle_feed")
        self.assertEqual(pet.offer_locked_until, 40.0)

    def test_update_dispatches_to_registered_handler(self):
        runtime = SimpleNamespace(
            offer_scene=ActiveItemScene(
                item_kind="honey",
                scene_kind="honey_guard",
                actor_name="Sirius Symboli",
                target_name="Tsurumaru Tsuyoshi",
            )
        )
        coordinator = ItemSceneCoordinator()
        calls = []

        def handler(now):
            calls.append(now)
            return True

        result = coordinator.update(
            runtime,
            12.5,
            update_handlers={"honey_guard": handler},
            clear_scene_callback=lambda: None,
        )

        self.assertTrue(result.handled)
        self.assertFalse(result.scene_finished)
        self.assertEqual(calls, [12.5])

    def test_update_clears_unknown_scene_kind(self):
        runtime = SimpleNamespace(
            offer_scene=ActiveItemScene(
                item_kind="ramen",
                scene_kind="mystery",
                actor_name="Symboli Rudolf",
                target_name="Tokai Teio",
            )
        )
        coordinator = ItemSceneCoordinator()
        cleared = []

        def clear():
            cleared.append(True)
            runtime.offer_scene = None

        result = coordinator.update(
            runtime,
            5.0,
            update_handlers={},
            clear_scene_callback=clear,
        )

        self.assertTrue(result.handled)
        self.assertTrue(result.scene_finished)
        self.assertEqual(cleared, [True])

    def test_build_shared_food_scene_initializes_names_and_stage_start(self):
        coordinator = ItemSceneCoordinator()

        scene = coordinator.build_scene(
            scene_kind="shared_food",
            item_kind="ramen",
            actor_name="Symboli Rudolf",
            target_name="Tokai Teio",
            stage="partner_approach",
            stage_started_at=10.0,
            stage_ends_at=12.5,
        )

        self.assertEqual(scene.stage_started_at, 10.0)
        self.assertEqual(scene.stage_ends_at, 12.5)
        self.assertEqual(scene.shared_food_state.holder_name, "Symboli Rudolf")
        self.assertEqual(scene.shared_food_state.partner_name, "Tokai Teio")
        self.assertFalse(scene.shared_food_state.outcome_resolved)

    def test_shared_food_state_stores_only_the_first_outcome(self):
        state = SharedFoodSceneState(
            holder_name="Sirius Symboli",
            partner_name="Tokai Teio",
        )

        stored = state.store_outcome(
            outcome_key="share_both",
            available_outcomes=("share_both", "holder_keeps", "holder_gives"),
            normalized_outcome_weights=(
                ("share_both", 0.5),
                ("holder_keeps", 0.25),
                ("holder_gives", 0.25),
            ),
            outcome_roll=0.2,
            consume_order=("partner", "holder"),
            consumer_names=("Tokai Teio", "Sirius Symboli"),
        )
        replaced = state.store_outcome(
            outcome_key="holder_gives",
            available_outcomes=("holder_gives",),
            normalized_outcome_weights=(("holder_gives", 1.0),),
            outcome_roll=0.9,
            consume_order=("partner",),
            consumer_names=("Tokai Teio",),
        )

        self.assertTrue(stored)
        self.assertFalse(replaced)
        self.assertEqual(state.outcome_key, "share_both")
        self.assertEqual(state.first_consumer_name, "Tokai Teio")
        self.assertEqual(state.second_consumer_name, "Sirius Symboli")
        self.assertEqual(state.outcome_roll, 0.2)

    def test_active_scene_uses_distinct_shared_food_state_instances(self):
        first = ActiveItemScene()
        second = ActiveItemScene()

        first.shared_food_state.item_hidden = True

        self.assertTrue(first.shared_food_state.item_hidden)
        self.assertFalse(second.shared_food_state.item_hidden)


class SharedFoodProfileTests(unittest.TestCase):
    def test_active_profiles_use_the_three_bidirectional_pairs(self):
        profile = get_shared_food_profile("shared_meal_ramen")
        tea_profile = get_shared_food_profile("tea_chat")
        honey_profile = get_shared_food_profile("shared_honey")

        self.assertIsNotNone(profile)
        self.assertEqual(profile.allowed_holders, ("Symboli Rudolf", "Tokai Teio"))
        self.assertEqual(profile.partner_rules["Symboli Rudolf"], ("Tokai Teio",))
        self.assertEqual(profile.partner_rules["Tokai Teio"], ("Symboli Rudolf",))
        self.assertEqual(tea_profile.allowed_holders, ("Symboli Rudolf", "Air Groove"))
        self.assertEqual(tea_profile.partner_rules["Air Groove"], ("Symboli Rudolf",))
        self.assertEqual(honey_profile.allowed_holders, ("Sirius Symboli", "Tokai Teio"))
        self.assertEqual(honey_profile.partner_rules["Tokai Teio"], ("Sirius Symboli",))
        self.assertEqual(profile.fallback_mode, "wait_short_then_solo")
        self.assertEqual(profile.partner_wait_seconds, 2.5)

    def test_item_lookup_activates_honey_and_leaves_lollipop_direct(self):
        tea_profile = get_shared_food_profile_for_item("tea")
        honey_profile = get_shared_food_profile_for_item("honey")
        lollipop_profile = get_shared_food_profile_for_item("lollipop")

        self.assertIsNotNone(tea_profile)
        self.assertEqual(tea_profile.profile_key, "tea_chat")
        self.assertIsNotNone(honey_profile)
        self.assertEqual(honey_profile.profile_key, "shared_honey")
        self.assertIsNone(lollipop_profile)

    def test_holder_lookup_excludes_non_pair_honey_recipient(self):
        self.assertIsNotNone(get_shared_food_profile_for_holder("honey", "Sirius Symboli"))
        self.assertIsNotNone(get_shared_food_profile_for_holder("honey", "Tokai Teio"))
        self.assertIsNone(get_shared_food_profile_for_holder("honey", "Tsurumaru Tsuyoshi"))
        self.assertEqual(
            get_shared_food_partner_names("honey", "Sirius Symboli"),
            ("Tokai Teio",),
        )
        self.assertEqual(
            get_shared_food_partner_names("honey", "Tokai Teio"),
            ("Sirius Symboli",),
        )

    def test_outcome_model_defines_consume_order(self):
        self.assertEqual(
            SHARED_FOOD_OUTCOME_DEFINITIONS_BY_KEY[
                SHARED_FOOD_OUTCOME_SHARE_BOTH
            ].consume_order,
            ("partner", "holder"),
        )
        self.assertEqual(
            SHARED_FOOD_OUTCOME_DEFINITIONS_BY_KEY[
                SHARED_FOOD_OUTCOME_HOLDER_KEEPS
            ].consume_order,
            ("holder",),
        )
        self.assertEqual(
            SHARED_FOOD_OUTCOME_DEFINITIONS_BY_KEY[
                SHARED_FOOD_OUTCOME_HOLDER_GIVES
            ].consume_order,
            ("partner",),
        )

    def test_profiles_define_normalized_weights_and_first_consume_visibility(self):
        for item_kind in ("ramen", "tea", "honey"):
            profile = get_shared_food_profile_for_item(item_kind)

            self.assertAlmostEqual(sum(profile.outcome_weights_by_key.values()), 1.0)
            self.assertEqual(profile.consume_mode, "weighted_outcome")
            self.assertEqual(profile.item_visibility_phase, "until_first_consume")
            self.assertEqual(profile.join_distance, 500.0)

    def test_tea_partner_moods_cover_air_groove_shared_watch(self):
        profile = get_shared_food_profile_for_item("tea")

        self.assertIn("awkward", profile.partner_preferred_moods)

    def test_character_capabilities_are_item_specific_not_role_specific(self):
        ramen_profile = get_shared_food_profile_for_item("ramen")
        tea_profile = get_shared_food_profile_for_item("tea")
        honey_profile = get_shared_food_profile_for_item("honey")

        rudolf_ramen = ramen_profile.capabilities_for("Symboli Rudolf")
        rudolf_tea = tea_profile.capabilities_for("Symboli Rudolf")
        teio_honey = honey_profile.capabilities_for("Tokai Teio")

        self.assertEqual(rudolf_ramen.consume_candidates, (("idle", "side_sit_ramen"),))
        self.assertEqual(rudolf_tea.consume_candidates, (("idle", "side_drink"),))
        self.assertIn(("idle", "side_sit_drink"), teio_honey.consume_candidates)
        for capabilities in (
            rudolf_ramen,
            ramen_profile.capabilities_for("Tokai Teio"),
            rudolf_tea,
            tea_profile.capabilities_for("Air Groove"),
            honey_profile.capabilities_for("Sirius Symboli"),
            teio_honey,
        ):
            self.assertTrue(capabilities.hold_candidates)
            self.assertTrue(capabilities.approach_candidates)
            self.assertTrue(capabilities.consume_candidates)
            self.assertTrue(capabilities.watch_candidates)
            self.assertTrue(capabilities.react_candidates)


if __name__ == "__main__":
    unittest.main()
