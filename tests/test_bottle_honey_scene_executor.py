import unittest
from types import SimpleNamespace
from unittest.mock import Mock

try:
    from tanuki_core.bottle_honey_scene_executor import BottleHoneySceneExecutor
except (ImportError, ModuleNotFoundError) as exc:
    BottleHoneySceneExecutor = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


@unittest.skipIf(BottleHoneySceneExecutor is None, f"runtime imports unavailable: {IMPORT_ERROR}")
class BottleHoneySceneExecutorTests(unittest.TestCase):
    def setUp(self):
        self.executor = BottleHoneySceneExecutor()

    def test_bottle_start_keeps_held_behavior_without_available_child(self):
        holder_pet = SimpleNamespace(name="Symboli Rudolf")
        runtime = SimpleNamespace(
            ensure_pet_held_item=Mock(),
            choose_bottle_feed_child_for_holder=Mock(return_value=None),
            apply_held_item_behavior=Mock(return_value=True),
        )

        result = self.executor.start_bottle_feed_scene(
            runtime,
            holder_pet,
            source="ground",
            now=10.0,
        )

        self.assertTrue(result)
        runtime.ensure_pet_held_item.assert_called_once_with(holder_pet, "bottle", source="ground")
        runtime.apply_held_item_behavior.assert_called_once_with(holder_pet, 10.0)

    def test_bottle_start_delegates_two_participant_scene_lock(self):
        holder_pet = SimpleNamespace(name="Tokai Teio")
        child_pet = SimpleNamespace(name="Tsurumaru Tsuyoshi")
        coordinator = Mock()
        coordinator.start_scene.return_value = SimpleNamespace(started=True)
        runtime = SimpleNamespace(
            ensure_pet_held_item=Mock(),
            choose_bottle_feed_child_for_holder=Mock(return_value=child_pet),
            pet_is_window_transitioning_for_offer=Mock(return_value=False),
            prepare_pet_window_state_for_offer=Mock(return_value=False),
            interrupt_pet_window_motion_for_offer=Mock(),
            item_scene_coordinator=coordinator,
            apply_held_item_behavior=Mock(return_value=True),
            refresh_offer_scene_locks=Mock(),
        )

        result = self.executor.start_bottle_feed_scene(
            runtime,
            holder_pet,
            source="offer_tray",
            now=20.0,
        )

        self.assertTrue(result)
        coordinator.start_scene.assert_called_once_with(
            runtime,
            participant_pets=(holder_pet, child_pet),
            item_kind="bottle",
            scene_kind="bottle_feed",
            actor_name=holder_pet.name,
            target_name=child_pet.name,
            stage="approach",
            stage_initialized=False,
            stage_ends_at=3620.0,
            scene_ends_at=3620.0,
            source="offer_tray",
        )
        self.assertEqual(runtime.interrupt_pet_window_motion_for_offer.call_count, 2)
        runtime.apply_held_item_behavior.assert_called_once_with(holder_pet, 20.0)
        runtime.refresh_offer_scene_locks.assert_called_once_with(holder_pet, child_pet)

    def test_bottle_completion_rewards_and_records_once(self):
        holder_pet = SimpleNamespace(name="Tokai Teio")
        child_pet = SimpleNamespace(name="Tsurumaru Tsuyoshi", isVisible=Mock(return_value=True))
        scene = SimpleNamespace(
            actor_name=holder_pet.name,
            target_name=child_pet.name,
            stage="drink",
            scene_ends_at=25.0,
            event_recorded=False,
            source="ground",
        )
        runtime = SimpleNamespace(
            offer_scene=scene,
            find_pet_by_name=Mock(side_effect=lambda name, visible_only=False: {
                holder_pet.name: holder_pet,
                child_pet.name: child_pet,
            }.get(name)),
            pet_is_window_transitioning_for_offer=Mock(return_value=False),
            prepare_pet_window_state_for_offer=Mock(return_value=False),
            refresh_offer_scene_locks=Mock(),
            apply_offer_mood_reward=Mock(),
            record_offer_event=Mock(),
            clear_offer_scene=Mock(),
        )

        result = self.executor.update_bottle_feed_scene(runtime, now=25.0)

        self.assertTrue(result)
        runtime.apply_offer_mood_reward.assert_called_once_with(child_pet.name)
        runtime.record_offer_event.assert_called_once_with(
            "bottle",
            holder_pet.name,
            child_pet.name,
            "bottle_feed",
            source="ground",
        )
        self.assertTrue(scene.event_recorded)
        runtime.clear_offer_scene.assert_called_once_with()

    def test_honey_start_keeps_held_behavior_without_guardian(self):
        child_pet = SimpleNamespace(name="Tsurumaru Tsuyoshi")
        runtime = SimpleNamespace(
            ensure_pet_held_item=Mock(),
            choose_honey_guardian_for_child=Mock(return_value=""),
            apply_held_item_behavior=Mock(return_value=True),
        )

        result = self.executor.start_honey_guard_scene(
            runtime,
            child_pet,
            source="ground",
            now=30.0,
        )

        self.assertTrue(result)
        runtime.ensure_pet_held_item.assert_called_once_with(child_pet, "honey", source="ground")
        runtime.apply_held_item_behavior.assert_called_once_with(child_pet, 30.0)

    def test_honey_start_releases_sleep_activity_before_scene_lock(self):
        sleep_state = SimpleNamespace(active=True, activity_kind="sleep")

        def interrupt_sleep(_pet, *, reason):
            self.assertEqual(reason, "honey_guard")
            sleep_state.active = False
            sleep_state.activity_kind = "none"
            return True

        guardian_pet = SimpleNamespace(
            name="Sirius Symboli",
            activity_state=sleep_state,
            activity_user_interrupt_provider=Mock(side_effect=interrupt_sleep),
        )
        child_pet = SimpleNamespace(name="Tsurumaru Tsuyoshi")
        coordinator = Mock()
        coordinator.start_scene.return_value = SimpleNamespace(started=True)
        runtime = SimpleNamespace(
            ensure_pet_held_item=Mock(),
            choose_honey_guardian_for_child=Mock(
                return_value=guardian_pet.name
            ),
            find_pet_by_name=Mock(return_value=guardian_pet),
            pet_is_window_transitioning_for_offer=Mock(return_value=False),
            prepare_pet_window_state_for_offer=Mock(return_value=False),
            interrupt_pet_window_motion_for_offer=Mock(),
            item_scene_coordinator=coordinator,
            apply_held_item_behavior=Mock(return_value=True),
            refresh_offer_scene_locks=Mock(),
        )

        result = self.executor.start_honey_guard_scene(
            runtime,
            child_pet,
            source="offer_tray",
            now=40.0,
        )

        self.assertTrue(result)
        self.assertFalse(sleep_state.active)
        guardian_pet.activity_user_interrupt_provider.assert_called_once_with(
            guardian_pet,
            reason="honey_guard",
        )
        coordinator.start_scene.assert_called_once()


if __name__ == "__main__":
    unittest.main()
