import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from tanuki_core.app_runtime import TanukiAppRuntime
from tanuki_core.shared_food_profiles import get_shared_food_profile_for_item


class FakeSharedFoodWidget:
    def __init__(self):
        self.close_calls = 0
        self.delete_calls = 0
        self.show_calls = 0

    def close(self):
        self.close_calls += 1

    def deleteLater(self):
        self.delete_calls += 1

    def show(self):
        self.show_calls += 1


class FakeSharedFoodAssetManager:
    def __init__(self, supported_candidates):
        self.supported_candidates = set(supported_candidates)
        self.calls = []

    def get_frames_for_action_by_preferences(
        self,
        purpose,
        action_type,
        preferred_moods,
        forbidden=None,
        mood_score=None,
        context=None,
    ):
        self.calls.append((purpose, action_type, tuple(preferred_moods), context))
        if (purpose, action_type) not in self.supported_candidates:
            return None
        mood_tag = tuple(preferred_moods or ("happy",))[0]
        return [f"{purpose}:{action_type}:{mood_tag}"], action_type, mood_tag


class FakeSharedFoodPet:
    def __init__(self, name, x, supported_candidates):
        self.name = name
        self._visible = True
        self._x = float(x)
        self._y = 100.0
        self._width = 200
        self._height = 200
        self.direction = 1
        self.original_face_left = True
        self.state = "idle"
        self.state_timer = 0
        self.current_frames = []
        self.current_purpose = "idle"
        self.current_action_tag = "stand"
        self.current_mood_tag = "happy"
        self.mood_score = 50.0
        self.asset_manager = FakeSharedFoodAssetManager(supported_candidates)
        self.offer_scene_kind = "none"
        self.offer_locked_until = 0.0
        self.held_item_kind = ""
        self.held_item_source = "none"
        self.held_item_started_at = 0.0
        self.held_item_widget = None
        self.flight_mode = "none"
        self.perched_window_hwnd = 0
        self.dragging = False
        self.is_recovering = False
        self.social_mode = "none"
        self.is_angry_locked = False
        self.vy = 0.0
        self.fall_origin_y = None
        self.care_mode = "none"
        self.care_partner = None
        self.is_hugging = False
        self.care_lock_mode = "none"
        self.care_lock_end_time = 0.0
        self.perception_situation_tag = "stable"
        self.expression_animation_context = "ambient"
        self.expression_relation_overlay = "none"
        self.expression_focus_target_name = ""
        self.expression_posture_bias = "neutral"
        self.expression_spacing_bias = "neutral"
        self.expression_look_at_target = False
        self.relationship_focus_target_name = ""
        self.negative_afterglow_until = 0.0
        self.negative_afterglow_preferred_moods = ()
        self.negative_afterglow_forbidden_moods = ()
        self.offer_hover_reaction_cooldown_until = 0.0
        self.move_toward_calls = []
        self.refresh_calls = 0
        self.reset_calls = 0
        self.heart_calls = 0

    def isVisible(self):
        return self._visible

    def x(self):
        return self._x

    def y(self):
        return self._y

    def width(self):
        return self._width

    def height(self):
        return self._height

    def distance_to(self, other):
        return abs(self._x - other.x())

    def get_base_speed(self):
        return 2.0

    def move_toward_x(self, target_x, speed_scale=1.0, min_speed=None):
        self.move_toward_calls.append((target_x, speed_scale, min_speed))
        return True

    def reset_stationary_move_mode(self):
        self.reset_calls += 1

    def refresh_movement_state(self):
        self.refresh_calls += 1

    def apply_animation_result(self, purpose, result):
        if not result:
            return False
        frames, action_type, mood_tag = result
        self.current_frames = frames
        self.current_purpose = purpose
        self.current_action_tag = action_type
        self.current_mood_tag = mood_tag
        return True

    def is_under_care(self, now):
        return False

    def clear_negative_afterglow(self):
        self.negative_afterglow_until = 0.0
        self.negative_afterglow_preferred_moods = ()
        self.negative_afterglow_forbidden_moods = ()

    def sync_mood_state_with_score(self):
        return None

    def pop_heart(self):
        self.heart_calls += 1


def collect_profile_candidates(profile, pet_name):
    capabilities = profile.capabilities_for(pet_name)
    candidates = set()
    for capability_name in ("hold", "approach", "consume", "request", "watch", "react"):
        candidates.update(getattr(capabilities, f"{capability_name}_candidates"))
    return candidates


class SharedFoodRuntimeTests(unittest.TestCase):
    def build_runtime(self, item_kind="ramen", holder_name=None):
        profile = get_shared_food_profile_for_item(item_kind)
        holder_name = holder_name or profile.allowed_holders[0]
        partner_name = profile.partner_names_for_holder(holder_name)[0]
        holder = FakeSharedFoodPet(
            holder_name,
            100.0,
            collect_profile_candidates(profile, holder_name),
        )
        partner = FakeSharedFoodPet(
            partner_name,
            300.0,
            collect_profile_candidates(profile, partner_name),
        )
        runtime = TanukiAppRuntime(
            app=None,
            settings_provider=SimpleNamespace(world_mode="sandbox"),
            config_store=None,
            save_scheduler=None,
            window_tracker=None,
            pets_dict={},
            pets_list=[holder, partner],
            dashboard=SimpleNamespace(refresh_household_summary_if_open=lambda: None),
            sensor=None,
            monitor=None,
        )

        def ensure_held_item(pet, requested_item_kind, source="offer_tray"):
            widget = FakeSharedFoodWidget()
            pet.held_item_kind = requested_item_kind
            pet.held_item_source = source
            pet.held_item_started_at = 10.0
            pet.held_item_widget = widget
            return widget

        runtime.ensure_pet_held_item = ensure_held_item
        runtime.update_held_offer_widget_position = (
            lambda widget, pet, requested_item_kind, prefer_preview=False: widget.show()
            if widget is not None
            else None
        )
        return runtime, profile, holder, partner

    def start_scene(self, runtime, profile, holder, partner, roll=0.0):
        with patch("tanuki_core.app_runtime.app_now", return_value=10.0):
            return runtime.start_shared_food_scene(
                holder,
                partner,
                profile=profile,
                source="offer_tray",
                outcome_roll=roll,
            )

    def advance_to_request_decision(self, runtime, holder, partner):
        partner._x = holder.x() + 80.0
        runtime.update_shared_food_scene(runtime.offer_scene.stage_started_at + 0.1)
        self.assertEqual(runtime.offer_scene.stage, "request_decision")

    def advance_to_first_consume(self, runtime, holder, partner):
        self.advance_to_request_decision(runtime, holder, partner)
        runtime.update_shared_food_scene(runtime.offer_scene.stage_ends_at)
        self.assertEqual(runtime.offer_scene.stage, "first_consume")

    def test_start_scene_holds_one_item_without_resolving_outcome(self):
        runtime, profile, holder, partner = self.build_runtime()

        started = self.start_scene(runtime, profile, holder, partner, roll=0.0)

        self.assertTrue(started)
        self.assertEqual(runtime.offer_scene.stage, "partner_approach")
        self.assertFalse(runtime.offer_scene.shared_food_state.outcome_resolved)
        self.assertEqual(holder.held_item_kind, "ramen")
        self.assertEqual(holder.held_item_widget.show_calls, 1)
        self.assertEqual(holder.offer_scene_kind, "shared_food")
        self.assertEqual(partner.offer_scene_kind, "shared_food")

    def test_first_consume_resolves_once_and_removes_external_item(self):
        runtime, profile, holder, partner = self.build_runtime()
        self.start_scene(runtime, profile, holder, partner, roll=0.0)
        widget = holder.held_item_widget

        self.advance_to_first_consume(runtime, holder, partner)
        shared_state = runtime.offer_scene.shared_food_state

        self.assertEqual(shared_state.outcome_key, "share_both")
        self.assertEqual(shared_state.consumer_names, (partner.name, holder.name))
        self.assertTrue(shared_state.item_hidden)
        self.assertEqual(holder.held_item_kind, "")
        self.assertEqual(widget.close_calls, 1)
        self.assertEqual(widget.delete_calls, 1)
        self.assertEqual(partner.current_action_tag, "side_sit_ramen")
        self.assertEqual(holder.current_action_tag, "rest")
        runtime.update_shared_food_scene(runtime.offer_scene.stage_started_at + 0.1)
        self.assertEqual(widget.close_calls, 1)

    def test_all_six_directions_reach_first_consume(self):
        for item_kind in ("ramen", "tea", "honey"):
            profile = get_shared_food_profile_for_item(item_kind)
            for holder_name in profile.allowed_holders:
                with self.subTest(item_kind=item_kind, holder_name=holder_name):
                    runtime, profile, holder, partner = self.build_runtime(
                        item_kind,
                        holder_name=holder_name,
                    )
                    self.start_scene(runtime, profile, holder, partner, roll=0.0)
                    self.advance_to_first_consume(runtime, holder, partner)

                    self.assertEqual(
                        runtime.offer_scene.shared_food_state.consumer_names,
                        (partner.name, holder.name),
                    )
                    self.assertTrue(runtime.offer_scene.shared_food_state.item_hidden)

    def test_single_consumer_outcomes_skip_second_consume(self):
        cases = (
            (0.70, "holder_keeps", 0),
            (0.90, "holder_gives", 1),
        )
        for roll, expected_outcome, consumer_index in cases:
            with self.subTest(outcome=expected_outcome):
                runtime, profile, holder, partner = self.build_runtime()
                self.start_scene(runtime, profile, holder, partner, roll=roll)
                self.advance_to_first_consume(runtime, holder, partner)
                shared_state = runtime.offer_scene.shared_food_state

                self.assertEqual(shared_state.outcome_key, expected_outcome)
                self.assertEqual(
                    shared_state.consumer_names,
                    (holder.name, partner.name)[consumer_index:consumer_index + 1],
                )
                runtime.record_shared_food_event = Mock()
                runtime.apply_offer_mood_reward = Mock(return_value=True)
                runtime.update_shared_food_scene(runtime.offer_scene.stage_ends_at)
                self.assertEqual(runtime.offer_scene.stage, "finish")

    def test_share_both_runs_two_consume_turns_and_finishes_once(self):
        runtime, profile, holder, partner = self.build_runtime()
        self.start_scene(runtime, profile, holder, partner, roll=0.0)
        widget = holder.held_item_widget
        self.advance_to_first_consume(runtime, holder, partner)
        runtime.record_shared_food_event = Mock()
        runtime.apply_offer_mood_reward = Mock(return_value=True)

        runtime.update_shared_food_scene(runtime.offer_scene.stage_ends_at)
        self.assertEqual(runtime.offer_scene.stage, "transition")
        runtime.update_shared_food_scene(runtime.offer_scene.stage_ends_at)
        self.assertEqual(runtime.offer_scene.stage, "second_consume")
        self.assertEqual(holder.current_action_tag, "side_sit_ramen")
        self.assertEqual(partner.current_action_tag, "side_face")
        runtime.update_shared_food_scene(runtime.offer_scene.stage_ends_at)
        self.assertEqual(runtime.offer_scene.stage, "finish")
        self.assertTrue(runtime.offer_scene.shared_food_state.effects_applied)
        self.assertTrue(runtime.offer_scene.event_recorded)
        runtime.update_shared_food_scene(runtime.offer_scene.stage_started_at + 0.1)

        self.assertEqual(runtime.record_shared_food_event.call_count, 1)
        self.assertEqual(runtime.apply_offer_mood_reward.call_count, 2)
        finish_end = runtime.offer_scene.stage_ends_at
        runtime.update_shared_food_scene(finish_end)
        self.assertIsNone(runtime.offer_scene)
        self.assertEqual(widget.close_calls, 1)

    def test_clear_before_consume_removes_held_item_once(self):
        runtime, profile, holder, partner = self.build_runtime()
        self.start_scene(runtime, profile, holder, partner, roll=0.0)
        scene = runtime.offer_scene
        widget = holder.held_item_widget

        runtime.clear_offer_scene()
        runtime.clear_offer_scene()

        self.assertIsNone(runtime.offer_scene)
        self.assertTrue(scene.shared_food_state.item_hidden)
        self.assertEqual(holder.held_item_kind, "")
        self.assertEqual(widget.close_calls, 1)
        self.assertEqual(widget.delete_calls, 1)

    def test_unavailable_partner_before_consume_falls_back_to_solo(self):
        runtime, profile, holder, partner = self.build_runtime()
        self.start_scene(runtime, profile, holder, partner, roll=0.0)
        widget = holder.held_item_widget
        partner._visible = False
        runtime.start_direct_offer_scene = Mock(return_value=True)

        handled = runtime.update_shared_food_scene(10.1)

        self.assertTrue(handled)
        runtime.start_direct_offer_scene.assert_called_once_with(
            "ramen",
            holder,
            source="offer_tray",
        )
        self.assertIsNone(runtime.offer_scene)
        self.assertEqual(widget.close_calls, 1)

    def test_dragged_partner_during_approach_falls_back_to_solo(self):
        runtime, profile, holder, partner = self.build_runtime()
        self.start_scene(runtime, profile, holder, partner, roll=0.0)
        partner.dragging = True
        runtime.start_direct_offer_scene = Mock(return_value=True)

        handled = runtime.update_shared_food_scene(10.1)

        self.assertTrue(handled)
        runtime.start_direct_offer_scene.assert_called_once_with(
            "ramen",
            holder,
            source="offer_tray",
        )
        self.assertIsNone(runtime.offer_scene)

    def test_update_offer_scene_dispatches_shared_food_handler(self):
        runtime, profile, holder, partner = self.build_runtime()
        self.start_scene(runtime, profile, holder, partner, roll=0.0)
        runtime.update_shared_food_scene = Mock(return_value=True)

        handled = runtime.update_offer_scene(now=10.1)

        self.assertTrue(handled)
        runtime.update_shared_food_scene.assert_called_once_with(10.1)

    def test_shared_food_capability_contexts_include_approach_and_consume_fallback(self):
        runtime, profile, holder, partner = self.build_runtime()

        self.assertEqual(
            runtime.get_shared_food_capability_contexts("ramen", holder.name, "approach"),
            ("shared_food_approach",),
        )
        self.assertEqual(
            runtime.get_shared_food_capability_contexts("ramen", holder.name, "consume"),
            ("shared_food_consume", "offer_accept_ramen"),
        )

    def test_stage_contexts_follow_request_watch_consume_react_roles(self):
        runtime, profile, holder, partner = self.build_runtime()

        self.start_scene(runtime, profile, holder, partner, roll=0.0)
        self.assertEqual(holder.asset_manager.calls[-1][3], "shared_food_hold")
        self.assertEqual(partner.asset_manager.calls[-1][3], "shared_food_approach")

        self.advance_to_request_decision(runtime, holder, partner)
        self.assertEqual(holder.asset_manager.calls[-1][3], "shared_food_watch")
        self.assertEqual(partner.asset_manager.calls[-1][3], "shared_food_request")

        runtime.update_shared_food_scene(runtime.offer_scene.stage_ends_at)
        self.assertEqual(runtime.offer_scene.stage, "first_consume")
        self.assertEqual(holder.asset_manager.calls[-1][3], "shared_food_react")
        self.assertEqual(partner.asset_manager.calls[-1][3], "shared_food_consume")

        runtime.update_shared_food_scene(runtime.offer_scene.stage_ends_at)
        runtime.update_shared_food_scene(runtime.offer_scene.stage_ends_at)
        self.assertEqual(runtime.offer_scene.stage, "second_consume")
        self.assertEqual(holder.asset_manager.calls[-1][3], "shared_food_consume")
        self.assertEqual(partner.asset_manager.calls[-1][3], "shared_food_react")

    def test_approach_timeout_is_distance_aware_and_bounded(self):
        runtime, profile, holder, partner = self.build_runtime()

        self.start_scene(runtime, profile, holder, partner, roll=0.0)

        timeout = runtime.offer_scene.stage_ends_at - runtime.offer_scene.stage_started_at
        self.assertAlmostEqual(timeout, 3.7)
        self.assertLessEqual(timeout, 8.0)

    def test_all_six_offer_routes_start_shared_food(self):
        for item_kind in ("ramen", "tea", "honey"):
            profile = get_shared_food_profile_for_item(item_kind)
            for holder_name in profile.allowed_holders:
                with self.subTest(item_kind=item_kind, holder_name=holder_name):
                    runtime, profile, holder, partner = self.build_runtime(
                        item_kind,
                        holder_name=holder_name,
                    )
                    runtime.start_direct_offer_scene = Mock(return_value=True)
                    runtime.start_shared_food_scene = Mock(return_value=True)

                    handled = runtime.start_offer_interaction_for_target(item_kind, holder)

                    self.assertTrue(handled)
                    runtime.start_shared_food_scene.assert_called_once_with(
                        holder,
                        partner,
                        profile=profile,
                        source="offer_tray",
                    )
                    runtime.start_direct_offer_scene.assert_not_called()

    def test_ground_pickup_uses_same_shared_food_route_and_source(self):
        runtime, profile, holder, partner = self.build_runtime()
        runtime.start_direct_offer_scene = Mock(return_value=True)
        runtime.start_shared_food_scene = Mock(return_value=True)

        handled = runtime.start_offer_interaction_for_target(
            "ramen",
            holder,
            source="ground_pickup",
        )

        self.assertTrue(handled)
        runtime.start_shared_food_scene.assert_called_once_with(
            holder,
            partner,
            profile=profile,
            source="ground_pickup",
        )
        runtime.start_direct_offer_scene.assert_not_called()

    def test_unavailable_partner_routes_to_direct_accept(self):
        runtime, profile, holder, partner = self.build_runtime()
        partner._visible = False
        runtime.start_direct_offer_scene = Mock(return_value=True)
        runtime.start_shared_food_scene = Mock(return_value=True)

        handled = runtime.start_offer_interaction_for_target("ramen", holder)

        self.assertTrue(handled)
        runtime.start_shared_food_scene.assert_not_called()
        runtime.start_direct_offer_scene.assert_called_once_with(
            "ramen",
            holder,
            source="offer_tray",
        )

    def test_partner_beyond_join_distance_routes_to_direct_accept(self):
        runtime, profile, holder, partner = self.build_runtime()
        partner._x = holder.x() + profile.join_distance + 1.0
        runtime.start_direct_offer_scene = Mock(return_value=True)
        runtime.start_shared_food_scene = Mock(return_value=True)

        handled = runtime.start_offer_interaction_for_target("ramen", holder)

        self.assertTrue(handled)
        runtime.start_shared_food_scene.assert_not_called()
        runtime.start_direct_offer_scene.assert_called_once_with(
            "ramen",
            holder,
            source="offer_tray",
        )

    def test_partner_at_join_distance_can_start_shared_food(self):
        runtime, profile, holder, partner = self.build_runtime()
        partner._x = holder.x() + profile.join_distance
        runtime.start_direct_offer_scene = Mock(return_value=True)
        runtime.start_shared_food_scene = Mock(return_value=True)

        handled = runtime.start_offer_interaction_for_target("ramen", holder)

        self.assertTrue(handled)
        runtime.start_shared_food_scene.assert_called_once_with(
            holder,
            partner,
            profile=profile,
            source="offer_tray",
        )
        runtime.start_direct_offer_scene.assert_not_called()

    def test_start_scene_revalidates_partner_distance(self):
        runtime, profile, holder, partner = self.build_runtime()
        partner._x = holder.x() + profile.join_distance + 1.0

        started = self.start_scene(runtime, profile, holder, partner, roll=0.0)

        self.assertFalse(started)
        self.assertIsNone(runtime.offer_scene)
        self.assertIsNone(holder.held_item_widget)

    def test_busy_partner_routes_to_direct_accept(self):
        runtime, profile, holder, partner = self.build_runtime()
        partner.care_mode = "care_interaction"
        runtime.start_direct_offer_scene = Mock(return_value=True)
        runtime.start_shared_food_scene = Mock(return_value=True)

        handled = runtime.start_offer_interaction_for_target("ramen", holder)

        self.assertTrue(handled)
        runtime.start_shared_food_scene.assert_not_called()
        runtime.start_direct_offer_scene.assert_called_once_with(
            "ramen",
            holder,
            source="offer_tray",
        )

    def test_socially_busy_partner_routes_to_direct_accept(self):
        runtime, profile, holder, partner = self.build_runtime()
        partner.social_mode = "following"
        runtime.start_direct_offer_scene = Mock(return_value=True)
        runtime.start_shared_food_scene = Mock(return_value=True)

        handled = runtime.start_offer_interaction_for_target("ramen", holder)

        self.assertTrue(handled)
        runtime.start_shared_food_scene.assert_not_called()
        runtime.start_direct_offer_scene.assert_called_once_with(
            "ramen",
            holder,
            source="offer_tray",
        )

    def test_shared_food_start_failure_routes_to_direct_accept(self):
        runtime, profile, holder, partner = self.build_runtime()
        runtime.start_direct_offer_scene = Mock(return_value=True)
        runtime.start_shared_food_scene = Mock(return_value=False)

        handled = runtime.start_offer_interaction_for_target("ramen", holder)

        self.assertTrue(handled)
        runtime.start_shared_food_scene.assert_called_once_with(
            holder,
            partner,
            profile=profile,
            source="offer_tray",
        )
        runtime.start_direct_offer_scene.assert_called_once_with(
            "ramen",
            holder,
            source="offer_tray",
        )

    def test_honey_guard_keeps_priority_over_shared_food(self):
        runtime, profile, holder, partner = self.build_runtime("honey")
        tsuyoshi = FakeSharedFoodPet("Tsurumaru Tsuyoshi", 260.0, set())
        runtime.pets_list.append(tsuyoshi)
        runtime.start_honey_guard_scene = Mock(return_value=True)
        runtime.start_shared_food_scene = Mock(return_value=True)
        runtime.start_direct_offer_scene = Mock(return_value=True)

        with patch(
            "tanuki_core.app_runtime.get_shared_food_profile_for_holder",
            return_value=profile,
        ) as get_profile:
            handled = runtime.start_offer_interaction_for_target("honey", tsuyoshi)

        self.assertTrue(handled)
        runtime.start_honey_guard_scene.assert_called_once_with(
            tsuyoshi,
            source="offer_tray",
        )
        get_profile.assert_not_called()
        runtime.start_shared_food_scene.assert_not_called()
        runtime.start_direct_offer_scene.assert_not_called()

    def test_bottle_routes_keep_priority_over_shared_food(self):
        runtime, profile, adult, partner = self.build_runtime()
        tsuyoshi = FakeSharedFoodPet("Tsurumaru Tsuyoshi", 260.0, set())
        runtime.pets_list.append(tsuyoshi)
        runtime.start_bottle_feed_scene = Mock(return_value=True)
        runtime.start_shared_food_scene = Mock(return_value=True)
        runtime.start_direct_offer_scene = Mock(return_value=True)

        with patch(
            "tanuki_core.app_runtime.get_shared_food_profile_for_holder",
            return_value=profile,
        ) as get_profile:
            adult_handled = runtime.start_offer_interaction_for_target("bottle", adult)
            child_handled = runtime.start_offer_interaction_for_target("bottle", tsuyoshi)

        self.assertTrue(adult_handled)
        self.assertTrue(child_handled)
        runtime.start_bottle_feed_scene.assert_called_once_with(
            adult,
            source="offer_tray",
        )
        runtime.start_direct_offer_scene.assert_called_once_with(
            "bottle",
            tsuyoshi,
            source="offer_tray",
        )
        self.assertEqual(get_profile.call_count, 0)
        runtime.start_shared_food_scene.assert_not_called()

    def test_lollipop_remains_direct_accept(self):
        runtime, profile, holder, partner = self.build_runtime()
        runtime.start_direct_offer_scene = Mock(return_value=True)
        runtime.start_shared_food_scene = Mock(return_value=True)

        handled = runtime.start_offer_interaction_for_target("lollipop", holder)

        self.assertTrue(handled)
        runtime.start_direct_offer_scene.assert_called_once_with(
            "lollipop",
            holder,
            source="offer_tray",
        )
        runtime.start_shared_food_scene.assert_not_called()


if __name__ == "__main__":
    unittest.main()
