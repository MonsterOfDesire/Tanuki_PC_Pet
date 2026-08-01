import unittest

from tanuki_core.offer_interaction_rules import (
    GROUND_ITEM_LIFETIME_SECONDS,
    GROUND_ITEM_PICKUP_RADIUS,
    ITEM_BOTTLE,
    ITEM_HONEY,
    ITEM_LOLLIPOP,
    ITEM_RAMEN,
    ITEM_TEA,
    OfferGuardianCandidate,
    can_pet_interact_with_offer_item,
    choose_honey_guardian,
    get_direct_offer_accept_candidates,
    get_direct_offer_accept_context,
    get_direct_offer_accept_purpose_order,
    get_direct_offer_candidates,
    get_direct_offer_mobile_move_speed_scale,
    get_direct_offer_preview_context,
    get_direct_offer_preview_candidates,
    get_denied_offer_forbidden_moods,
    get_denied_offer_context,
    get_denied_offer_reaction_candidates,
    get_bottle_feed_child_approach_candidates,
    get_bottle_feed_child_approach_context,
    get_bottle_feed_child_drink_context,
    get_bottle_feed_holder_idle_context,
    get_bottle_feed_holder_watch_context,
    get_ground_pickup_pet_names,
    get_honey_guardian_move_candidates,
    get_honey_guardian_move_context,
    get_honey_guardian_take_candidates,
    get_honey_guardian_take_context,
    get_offer_hover_reaction_variants,
    get_offer_hover_timeout_stage_context,
    get_offer_item_definition,
    get_offer_item_definitions,
    resolve_offer_hotspot_match,
    resolve_offer_preview_match,
)


class OfferInteractionRulesTests(unittest.TestCase):
    def test_get_offer_item_definitions_returns_all_food_items_in_tray_order(self):
        items = get_offer_item_definitions()

        self.assertEqual(
            [item.kind for item in items],
            [ITEM_RAMEN, ITEM_HONEY, ITEM_TEA, ITEM_BOTTLE, ITEM_LOLLIPOP],
        )

    def test_get_offer_item_definition_returns_item_metadata(self):
        item_definition = get_offer_item_definition(ITEM_HONEY)

        self.assertIsNotNone(item_definition)
        self.assertEqual(item_definition.icon_relative_path, "items/honey.png")

    def test_get_ground_pickup_pet_names_returns_supported_pets(self):
        ramen_pets = get_ground_pickup_pet_names(ITEM_RAMEN)
        honey_pets = get_ground_pickup_pet_names(ITEM_HONEY)
        tea_pets = get_ground_pickup_pet_names(ITEM_TEA)
        bottle_pets = get_ground_pickup_pet_names(ITEM_BOTTLE)
        lollipop_pets = get_ground_pickup_pet_names(ITEM_LOLLIPOP)

        self.assertEqual(ramen_pets, ["Symboli Rudolf", "Tokai Teio"])
        self.assertEqual(honey_pets, ["Sirius Symboli", "Tokai Teio", "Tsurumaru Tsuyoshi"])
        self.assertEqual(tea_pets, ["Symboli Rudolf", "Air Groove"])
        self.assertEqual(
            bottle_pets,
            ["Symboli Rudolf", "Sirius Symboli", "Tokai Teio", "Tsurumaru Tsuyoshi", "Air Groove"],
        )
        self.assertEqual(lollipop_pets, ["Symboli Rudolf", "Tokai Teio"])
        self.assertEqual(GROUND_ITEM_LIFETIME_SECONDS, 60.0)
        self.assertEqual(GROUND_ITEM_PICKUP_RADIUS, 55.0)

    def test_can_pet_interact_with_offer_item_matches_item_specific_hotspots(self):
        self.assertTrue(can_pet_interact_with_offer_item(ITEM_RAMEN, "Symboli Rudolf"))
        self.assertTrue(can_pet_interact_with_offer_item(ITEM_RAMEN, "Tokai Teio"))
        self.assertFalse(can_pet_interact_with_offer_item(ITEM_RAMEN, "Air Groove"))

        self.assertTrue(can_pet_interact_with_offer_item(ITEM_TEA, "Air Groove"))
        self.assertFalse(can_pet_interact_with_offer_item(ITEM_TEA, "Tokai Teio"))

        self.assertTrue(can_pet_interact_with_offer_item(ITEM_BOTTLE, "Sirius Symboli"))
        self.assertTrue(can_pet_interact_with_offer_item(ITEM_BOTTLE, "Tsurumaru Tsuyoshi"))

        self.assertTrue(can_pet_interact_with_offer_item(ITEM_HONEY, "Tsurumaru Tsuyoshi"))
        self.assertFalse(can_pet_interact_with_offer_item(ITEM_HONEY, "Symboli Rudolf"))

    def test_choose_honey_guardian_prefers_nearest_visible_guardian(self):
        guardian_name = choose_honey_guardian(
            [
                OfferGuardianCandidate(name="Sirius Symboli", distance=120.0, is_visible=True),
                OfferGuardianCandidate(name="Symboli Rudolf", distance=90.0, is_visible=True),
            ]
        )

        self.assertEqual(guardian_name, "Symboli Rudolf")

    def test_resolve_offer_hotspot_match_uses_unflipped_hotspot_position(self):
        match = resolve_offer_hotspot_match(
            item_kind=ITEM_BOTTLE,
            pet_name="Tsurumaru Tsuyoshi",
            widget_left=100,
            widget_top=200,
            widget_width=240,
            widget_height=240,
            frame_width=120,
            frame_height=220,
            render_scale=1.0,
            direction=-1,
            original_face_left=True,
            offer_global_x=181,
            offer_global_y=396,
        )

        self.assertTrue(match.matched)
        self.assertLess(match.distance, match.hotspot_radius)

    def test_resolve_offer_hotspot_match_flips_x_when_pet_faces_other_side(self):
        left_match = resolve_offer_hotspot_match(
            item_kind=ITEM_BOTTLE,
            pet_name="Tsurumaru Tsuyoshi",
            widget_left=100,
            widget_top=200,
            widget_width=240,
            widget_height=240,
            frame_width=120,
            frame_height=220,
            render_scale=1.0,
            direction=-1,
            original_face_left=True,
            offer_global_x=181,
            offer_global_y=396,
        )
        flipped_match = resolve_offer_hotspot_match(
            item_kind=ITEM_BOTTLE,
            pet_name="Tsurumaru Tsuyoshi",
            widget_left=100,
            widget_top=200,
            widget_width=240,
            widget_height=240,
            frame_width=120,
            frame_height=220,
            render_scale=1.0,
            direction=1,
            original_face_left=True,
            offer_global_x=259,
            offer_global_y=396,
        )

        self.assertTrue(left_match.matched)
        self.assertTrue(flipped_match.matched)
        self.assertNotEqual(left_match.hotspot_global_x, flipped_match.hotspot_global_x)

    def test_resolve_offer_hotspot_match_scales_source_pixels_by_render_scale(self):
        match = resolve_offer_hotspot_match(
            item_kind=ITEM_HONEY,
            pet_name="Tokai Teio",
            widget_left=300,
            widget_top=100,
            widget_width=260,
            widget_height=260,
            frame_width=150,
            frame_height=180,
            render_scale=0.5,
            direction=-1,
            original_face_left=True,
            offer_global_x=385,
            offer_global_y=286,
        )

        self.assertTrue(match.matched)
        self.assertLess(match.distance, match.hotspot_radius)

    def test_transformed_teio_bottle_uses_form_specific_hotspot(self):
        match = resolve_offer_hotspot_match(
            item_kind=ITEM_BOTTLE,
            pet_name="Tokai Teio",
            widget_left=100,
            widget_top=200,
            widget_width=320,
            widget_height=320,
            frame_width=320,
            frame_height=320,
            render_scale=1.0,
            direction=-1,
            original_face_left=True,
            offer_global_x=123,
            offer_global_y=455,
            form_key="transformed",
        )

        self.assertTrue(match.matched)
        self.assertEqual(match.hotspot_global_x, 123.0)
        self.assertEqual(match.hotspot_global_y, 455.0)

    def test_resolve_offer_hotspot_match_requires_exact_radius(self):
        match = resolve_offer_hotspot_match(
            item_kind=ITEM_BOTTLE,
            pet_name="Tsurumaru Tsuyoshi",
            widget_left=100,
            widget_top=200,
            widget_width=240,
            widget_height=240,
            frame_width=120,
            frame_height=220,
            render_scale=1.0,
            direction=-1,
            original_face_left=True,
            offer_global_x=192,
            offer_global_y=396,
        )

        self.assertFalse(match.matched)
        self.assertGreater(match.distance, match.hotspot_radius)

    def test_resolve_offer_preview_match_detects_nearby_item_around_render_frame(self):
        match = resolve_offer_preview_match(
            widget_left=100,
            widget_top=200,
            widget_width=240,
            widget_height=240,
            frame_width=120,
            frame_height=220,
            offer_global_x=135,
            offer_global_y=250,
        )

        self.assertTrue(match.matched)

    def test_get_direct_offer_candidates_returns_expected_item_specific_actions(self):
        bottle_candidates = get_direct_offer_candidates(ITEM_BOTTLE, "Tsurumaru Tsuyoshi")
        rudolf_bottle_candidates = get_direct_offer_candidates(ITEM_BOTTLE, "Symboli Rudolf")
        honey_candidates = get_direct_offer_candidates(ITEM_HONEY, "Sirius Symboli")
        teio_honey_candidates = get_direct_offer_candidates(ITEM_HONEY, "Tokai Teio")
        tea_candidates = get_direct_offer_candidates(ITEM_TEA, "Air Groove")
        lollipop_candidates = get_direct_offer_candidates(ITEM_LOLLIPOP, "Tokai Teio")

        self.assertIn(("idle", "drink"), bottle_candidates)
        self.assertIn(("idle", "get"), rudolf_bottle_candidates)
        self.assertIn(("idle", "drink"), honey_candidates)
        self.assertIn(("move", "walk_drink"), teio_honey_candidates)
        self.assertIn(("idle", "drink"), tea_candidates)
        self.assertIn(("idle", "side_eat_candy"), lollipop_candidates)

    def test_get_direct_offer_preview_candidates_prefers_second_candidate(self):
        sirius_preview = get_direct_offer_preview_candidates(ITEM_HONEY, "Sirius Symboli")
        tsuyoshi_preview = get_direct_offer_preview_candidates(ITEM_BOTTLE, "Tsurumaru Tsuyoshi")
        tea_preview = get_direct_offer_preview_candidates(ITEM_TEA, "Air Groove")

        self.assertEqual(sirius_preview, [("idle", "stand_hand")])
        self.assertEqual(tsuyoshi_preview, [("idle", "get")])
        self.assertEqual(tea_preview, [("idle", "get")])

    def test_get_direct_offer_accept_candidates_prefers_first_candidate(self):
        sirius_accept = get_direct_offer_accept_candidates(ITEM_HONEY, "Sirius Symboli")
        tsuyoshi_accept = get_direct_offer_accept_candidates(ITEM_BOTTLE, "Tsurumaru Tsuyoshi")
        rudolf_bottle_accept = get_direct_offer_accept_candidates(ITEM_BOTTLE, "Symboli Rudolf")
        rudolf_tea_accept = get_direct_offer_accept_candidates(ITEM_TEA, "Symboli Rudolf")
        teio_ramen_accept = get_direct_offer_accept_candidates(ITEM_RAMEN, "Tokai Teio")

        self.assertEqual(sirius_accept, [("idle", "drink")])
        self.assertEqual(tsuyoshi_accept, [("idle", "drink")])
        self.assertEqual(rudolf_bottle_accept, [("idle", "get")])
        self.assertEqual(rudolf_tea_accept, [("idle", "side_drink")])
        self.assertEqual(teio_ramen_accept, [("idle", "side_sit_ramen")])

    def test_direct_offer_accept_purpose_order_can_choose_mobile_or_stationary_route(self):
        self.assertEqual(get_direct_offer_accept_purpose_order(ITEM_HONEY, "Tokai Teio", roll=0.49), ["move", "idle"])
        self.assertEqual(get_direct_offer_accept_purpose_order(ITEM_HONEY, "Tokai Teio", roll=0.50), ["idle", "move"])
        self.assertGreater(get_direct_offer_mobile_move_speed_scale(ITEM_HONEY, "Tokai Teio"), 0.0)

    def test_manifest_context_helpers_map_offer_scene_roles(self):
        self.assertEqual(get_direct_offer_preview_context(ITEM_HONEY, "Tsurumaru Tsuyoshi"), "offer_preview")
        self.assertEqual(get_direct_offer_accept_context(ITEM_BOTTLE, "Tsurumaru Tsuyoshi"), "offer_accept_milk")
        self.assertEqual(get_direct_offer_accept_context(ITEM_RAMEN, "Symboli Rudolf"), "offer_accept_ramen")
        self.assertEqual(get_direct_offer_accept_context(ITEM_TEA, "Air Groove"), "offer_accept_tea")
        self.assertEqual(get_direct_offer_accept_context(ITEM_LOLLIPOP, "Tokai Teio"), "offer_accept_lollipop")
        self.assertEqual(get_denied_offer_context("Tsurumaru Tsuyoshi"), "offer_denied")
        self.assertEqual(get_honey_guardian_move_context("Sirius Symboli"), "honey_guard_move")
        self.assertEqual(get_honey_guardian_take_context("Sirius Symboli"), "honey_guard_take")
        self.assertEqual(get_bottle_feed_holder_idle_context("Symboli Rudolf"), "bottle_feed_hold")
        self.assertEqual(get_bottle_feed_holder_watch_context("Symboli Rudolf"), "bottle_feed_watch")
        self.assertEqual(get_bottle_feed_child_approach_context("Tsurumaru Tsuyoshi"), "bottle_feed_child_approach")
        self.assertEqual(get_bottle_feed_child_drink_context("Tsurumaru Tsuyoshi"), "bottle_feed_child_drink")

    def test_scene_fallback_candidates_only_include_real_character_actions(self):
        self.assertEqual(
            get_honey_guardian_move_candidates("Symboli Rudolf"),
            [("move", "run_stretch"), ("move", "run")],
        )
        self.assertEqual(
            get_honey_guardian_take_candidates("Sirius Symboli"),
            [("idle", "stand_hand"), ("idle", "stand")],
        )
        self.assertEqual(
            get_denied_offer_reaction_candidates("Tsurumaru Tsuyoshi"),
            [
                ("idle", "side"),
                ("idle", "sit_no"),
                ("idle", "squat"),
                ("idle", "stand"),
                ("idle", "lie"),
            ],
        )
        self.assertEqual(
            get_bottle_feed_child_approach_candidates("Tsurumaru Tsuyoshi"),
            [("move", "climb")],
        )

    def test_offer_hover_timeout_context_maps_variant_route_and_stage(self):
        self.assertEqual(
            get_offer_hover_timeout_stage_context("Tsurumaru Tsuyoshi:bottle:variant_1", 0),
            "offer_timeout_route_a_step1",
        )
        self.assertEqual(
            get_offer_hover_timeout_stage_context("Tsurumaru Tsuyoshi:bottle:variant_1", 2),
            "offer_timeout_route_a_step3",
        )
        self.assertEqual(
            get_offer_hover_timeout_stage_context("Tsurumaru Tsuyoshi:bottle:variant_2", 1),
            "offer_timeout_route_b_step2",
        )

    def test_denied_offer_reaction_candidates_keep_lie_but_forbid_sleep_like_moods(self):
        denied_candidates = get_denied_offer_reaction_candidates("Tsurumaru Tsuyoshi")
        forbidden_moods = get_denied_offer_forbidden_moods()

        self.assertIn(("idle", "lie"), denied_candidates)
        self.assertIn(("idle", "side"), denied_candidates)
        self.assertIn(("idle", "squat"), denied_candidates)
        self.assertNotIn(("idle", "side_stand"), denied_candidates)
        self.assertIn("sleep", forbidden_moods)
        self.assertIn("exhausted", forbidden_moods)

    def test_hover_reaction_variants_expand_stage_matrix(self):
        variants = get_offer_hover_reaction_variants(ITEM_BOTTLE, "Tsurumaru Tsuyoshi")

        self.assertEqual(len(variants), 2)
        self.assertTrue(variants[0].avoid_cursor)
        self.assertEqual(variants[0].stages[0].purpose, "idle")
        self.assertEqual(variants[0].stages[0].action_type, "get")
        self.assertEqual(variants[0].stages[0].duration_seconds, 3.0)
        self.assertEqual(variants[0].stages[1].duration_seconds, 3.0)
        self.assertEqual(variants[1].stages[-1].mood_tag, "cry")

    def test_hover_reaction_variants_fallback_to_shared_template_for_new_items(self):
        variants = get_offer_hover_reaction_variants(ITEM_TEA, "Air Groove")

        self.assertEqual(len(variants), 2)
        self.assertTrue(variants[0].avoid_cursor)
        self.assertEqual(variants[0].stages[0].action_type, "get")


if __name__ == "__main__":
    unittest.main()
