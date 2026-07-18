import unittest
from unittest.mock import patch

from tanuki_core.pet_behavior_layers import PetBehaviorLayersMixin
from tanuki_core.pet_intent_rules import INTENT_OBSERVE, INTENT_POST_OBSERVE_INTERACTION
from tanuki_core.runtime import AdaptivePetLogicScheduler, SimulationClock


class FakeBehaviorLayerPet(PetBehaviorLayersMixin):
    def __init__(self):
        self.user_visible = True
        self.offer_scene_kind = "none"
        self.behavior_layer_refresh_skip_counter = 0
        self.behavior_layer_refresh_divisor = 1
        self.high_level_ai_refresh_skip_counter = 0
        self.high_level_ai_refresh_divisor = 1
        self.runtime_profiler = None
        self.perception_updates = 0
        self.relationship_updates = 0
        self.expression_updates = 0
        self.intent_syncs = 0
        self.override_updates = 0
        self.layer_refresh_results = []
        self.high_level_refresh_results = []

    def tick(self, all_pets):
        self.layer_refresh_results.append(self.refresh_behavior_layers(all_pets, now=1.0))
        self.high_level_refresh_results.append(self.should_refresh_high_level_ai())

    def apply_offer_behavior_layer_override(self):
        self.override_updates += 1

    def update_perception_state(self, all_pets):
        _ = all_pets
        self.perception_updates += 1

    def update_relationship_state(self, all_pets, now=None):
        _ = (all_pets, now)
        self.relationship_updates += 1

    def update_expression_state(self, all_pets, now=None):
        _ = (all_pets, now)
        self.expression_updates += 1

    def sync_intent_state(self, now=None):
        _ = now
        self.intent_syncs += 1


class FakeIntentSyncPet(PetBehaviorLayersMixin):
    def __init__(self):
        self.dragging = False
        self.is_angry_locked = False
        self.is_recovering = False
        self.care_mode = "none"
        self.care_target = None
        self.care_partner = None
        self.social_mode = "none"
        self.social_target = None
        self.flight_mode = "none"
        self.perched_window_hwnd = 0
        self.current_purpose = "idle"
        self.state = "idle"
        self.intent_kind = INTENT_OBSERVE
        self.intent_target_name = "Tokai Teio"
        self.intent_locked_until = 9.5
        self.intent_reconsider_after = 12.0
        self.intent_priority = 15
        self.intent_source = "ambient"
        self.intent_context = "observe"
        self.intent_reason = "observe_hold"
        self.relationship_focus_target_name = "Tokai Teio"
        self.expression_animation_context = "relation_watch"
        self.negative_afterglow_active = False

    def is_under_care(self, now):
        _ = now
        return False

    def is_negative_afterglow_active(self, now=None):
        _ = now
        return self.negative_afterglow_active


class PetBehaviorSchedulerTests(unittest.TestCase):
    def test_refresh_behavior_layers_runs_every_tick_at_1x(self):
        pet = FakeBehaviorLayerPet()

        with patch("tanuki_core.pet_behavior_layers.SIM_CLOCK.speed", 1.0):
            results = [pet.refresh_behavior_layers([], now=1.0), pet.refresh_behavior_layers([], now=1.1)]

        self.assertEqual(results, [True, True])
        self.assertEqual(pet.perception_updates, 2)
        self.assertEqual(pet.behavior_layer_refresh_divisor, 1)

    def test_refresh_behavior_layers_throttles_to_every_other_tick_at_4x(self):
        pet = FakeBehaviorLayerPet()

        with patch("tanuki_core.pet_behavior_layers.SIM_CLOCK.speed", 4.0):
            results = [
                pet.refresh_behavior_layers([], now=1.0),
                pet.refresh_behavior_layers([], now=1.1),
                pet.refresh_behavior_layers([], now=1.2),
                pet.refresh_behavior_layers([], now=1.3),
            ]

        self.assertEqual(results, [True, False, True, False])
        self.assertEqual(pet.perception_updates, 2)
        self.assertEqual(pet.behavior_layer_refresh_divisor, 2)

    def test_refresh_behavior_layers_throttles_more_aggressively_at_8x(self):
        pet = FakeBehaviorLayerPet()

        with patch("tanuki_core.pet_behavior_layers.SIM_CLOCK.speed", 8.0):
            results = [pet.refresh_behavior_layers([], now=1.0 + (index * 0.1)) for index in range(5)]

        self.assertEqual(results, [True, False, False, False, True])
        self.assertEqual(pet.perception_updates, 2)
        self.assertEqual(pet.behavior_layer_refresh_divisor, 4)

    def test_refresh_behavior_layers_consumes_accumulated_logic_delta_at_8x(self):
        pet = FakeBehaviorLayerPet()
        pet.logic_step_scale = 4.0

        with patch("tanuki_core.pet_behavior_layers.SIM_CLOCK.speed", 8.0):
            results = [pet.refresh_behavior_layers([], now=1.0), pet.refresh_behavior_layers([], now=1.1)]

        self.assertEqual(results, [True, True])
        self.assertEqual(pet.perception_updates, 2)

    def test_refresh_behavior_layers_resets_skip_counter_when_speed_bucket_changes(self):
        pet = FakeBehaviorLayerPet()

        with patch("tanuki_core.pet_behavior_layers.SIM_CLOCK.speed", 8.0):
            first = pet.refresh_behavior_layers([], now=1.0)
            second = pet.refresh_behavior_layers([], now=1.1)
        with patch("tanuki_core.pet_behavior_layers.SIM_CLOCK.speed", 1.0):
            third = pet.refresh_behavior_layers([], now=1.2)

        self.assertTrue(first)
        self.assertFalse(second)
        self.assertTrue(third)
        self.assertEqual(pet.perception_updates, 2)

    def test_refresh_behavior_layers_force_bypasses_scheduler(self):
        pet = FakeBehaviorLayerPet()

        with patch("tanuki_core.pet_behavior_layers.SIM_CLOCK.speed", 8.0):
            pet.refresh_behavior_layers([], now=1.0)
            skipped = pet.refresh_behavior_layers([], now=1.1)
            forced = pet.refresh_behavior_layers([], now=1.2, force=True)

        self.assertFalse(skipped)
        self.assertTrue(forced)
        self.assertEqual(pet.perception_updates, 2)

    def test_high_level_ai_refresh_runs_every_tick_at_1x(self):
        pet = FakeBehaviorLayerPet()

        with patch("tanuki_core.pet_behavior_layers.SIM_CLOCK.speed", 1.0):
            results = [pet.should_refresh_high_level_ai(), pet.should_refresh_high_level_ai()]

        self.assertEqual(results, [True, True])
        self.assertEqual(pet.high_level_ai_refresh_divisor, 1)

    def test_high_level_ai_refresh_throttles_at_4x(self):
        pet = FakeBehaviorLayerPet()

        with patch("tanuki_core.pet_behavior_layers.SIM_CLOCK.speed", 4.0):
            results = [
                pet.should_refresh_high_level_ai(),
                pet.should_refresh_high_level_ai(),
                pet.should_refresh_high_level_ai(),
                pet.should_refresh_high_level_ai(),
            ]

        self.assertEqual(results, [True, False, True, False])
        self.assertEqual(pet.high_level_ai_refresh_divisor, 2)

    def test_high_level_ai_refresh_throttles_more_aggressively_at_8x(self):
        pet = FakeBehaviorLayerPet()

        with patch("tanuki_core.pet_behavior_layers.SIM_CLOCK.speed", 8.0):
            results = [pet.should_refresh_high_level_ai() for _ in range(5)]

        self.assertEqual(results, [True, False, False, False, True])
        self.assertEqual(pet.high_level_ai_refresh_divisor, 4)

    def test_high_level_ai_refresh_consumes_fractional_accumulated_delta(self):
        pet = FakeBehaviorLayerPet()
        pet.logic_step_scale = 2.25

        with patch("tanuki_core.pet_behavior_layers.SIM_CLOCK.speed", 8.0):
            results = [pet.should_refresh_high_level_ai() for _ in range(3)]

        self.assertEqual(results, [True, False, True])

    def test_behavior_and_high_level_refresh_rates_match_across_pet_counts(self):
        low_load_scheduler = AdaptivePetLogicScheduler()
        high_load_scheduler = AdaptivePetLogicScheduler()
        two_pets = [FakeBehaviorLayerPet() for _ in range(2)]
        five_pets = [FakeBehaviorLayerPet() for _ in range(5)]

        with patch("tanuki_core.pet_behavior_layers.SIM_CLOCK.speed", 8.0):
            for _ in range(40):
                low_load_scheduler.run(two_pets, speed=8.0, step_delta=1.0)
                low_load_scheduler.run(two_pets, speed=8.0, step_delta=1.0)
                high_load_scheduler.run(five_pets, speed=8.0, step_delta=2.0)

        expected_refreshes = sum(two_pets[0].layer_refresh_results)
        self.assertEqual(expected_refreshes, 20)
        self.assertTrue(all(sum(pet.layer_refresh_results) == expected_refreshes for pet in two_pets))
        self.assertTrue(all(sum(pet.layer_refresh_results) == expected_refreshes for pet in five_pets))
        self.assertTrue(all(sum(pet.high_level_refresh_results) == expected_refreshes for pet in two_pets))
        self.assertTrue(all(sum(pet.high_level_refresh_results) == expected_refreshes for pet in five_pets))

    def test_behavior_refresh_rate_stays_close_with_real_8x_timer_delta(self):
        clock = SimulationClock()
        clock.speed = 8.0
        event_step_delta = clock.get_timer_step_delta(30, actual_interval_ms=8)
        repeat_count = clock.get_timer_repeat_count(30, minimum_interval_ms=8)
        repeated_step_delta = event_step_delta / repeat_count
        low_load_scheduler = AdaptivePetLogicScheduler()
        high_load_scheduler = AdaptivePetLogicScheduler()
        two_pets = [FakeBehaviorLayerPet() for _ in range(2)]
        five_pets = [FakeBehaviorLayerPet() for _ in range(5)]

        with patch("tanuki_core.pet_behavior_layers.SIM_CLOCK.speed", 8.0):
            for _ in range(120):
                for _repeat in range(repeat_count):
                    low_load_scheduler.run(two_pets, speed=8.0, step_delta=repeated_step_delta)
                high_load_scheduler.run(five_pets, speed=8.0, step_delta=event_step_delta)

        expected_layer_refreshes = sum(two_pets[0].layer_refresh_results)
        expected_ai_refreshes = sum(two_pets[0].high_level_refresh_results)
        self.assertEqual(expected_layer_refreshes, 64)
        self.assertEqual(expected_ai_refreshes, 64)
        self.assertTrue(
            all(abs(sum(pet.layer_refresh_results) - expected_layer_refreshes) <= 4 for pet in five_pets)
        )
        self.assertTrue(
            all(abs(sum(pet.high_level_refresh_results) - expected_ai_refreshes) <= 4 for pet in five_pets)
        )

    def test_sync_intent_state_preserves_expired_observe_for_executor_clear(self):
        pet = FakeIntentSyncPet()

        pet.sync_intent_state(now=10.0)

        self.assertEqual(pet.intent_kind, INTENT_OBSERVE)
        self.assertEqual(pet.intent_target_name, "Tokai Teio")
        self.assertEqual(pet.intent_context, "observe")
        self.assertEqual(pet.intent_reason, "observe_pending_clear")

    def test_sync_intent_state_preserves_expired_post_observe_for_executor_clear(self):
        pet = FakeIntentSyncPet()
        pet.intent_kind = INTENT_POST_OBSERVE_INTERACTION
        pet.intent_context = "post_observe_interaction"
        pet.intent_reason = "post_observe_interaction"

        pet.sync_intent_state(now=10.0)

        self.assertEqual(pet.intent_kind, INTENT_POST_OBSERVE_INTERACTION)
        self.assertEqual(pet.intent_target_name, "Tokai Teio")
        self.assertEqual(pet.intent_context, "post_observe_interaction")
        self.assertEqual(pet.intent_reason, "post_observe_interaction_pending_clear")

    def test_sync_intent_state_does_not_preserve_observe_lock_during_negative_afterglow(self):
        pet = FakeIntentSyncPet()
        pet.negative_afterglow_active = True

        pet.sync_intent_state(now=10.0)

        self.assertEqual(pet.intent_kind, "ambient_idle")
        self.assertEqual(pet.intent_target_name, "")
        self.assertEqual(pet.intent_locked_until, 0.0)


if __name__ == "__main__":
    unittest.main()
