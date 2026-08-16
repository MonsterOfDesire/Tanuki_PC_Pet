import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from tanuki_core.gameplay_app_adapter import GameplayAppAdapterMixin
from tanuki_core.gameplay_reward_adapter import GameplayRewardAdapter
from tanuki_core.household_app_adapter import HouseholdAppAdapterMixin


class GameplayRewardAdapterTests(unittest.TestCase):
    def test_mood_reward_updates_registered_pet_and_caps_score(self):
        pet = SimpleNamespace(
            transformation_state=None,
            mood_score=98.0,
            sync_mood_state_with_score=Mock(),
        )
        registry = SimpleNamespace(find_by_name=Mock(return_value=pet))
        adapter = GameplayRewardAdapter(
            pet_registry=registry,
            household=SimpleNamespace(),
        )

        self.assertTrue(adapter.apply_mood_reward("Tokai Teio", 6.0))

        self.assertEqual(pet.mood_score, 100.0)
        registry.find_by_name.assert_called_once_with(
            "Tokai Teio",
            visible_only=False,
        )
        pet.sync_mood_state_with_score.assert_called_once_with()

    def test_relationship_reward_updates_household_store(self):
        relationships = SimpleNamespace(apply_delta=Mock(return_value=True))
        adapter = GameplayRewardAdapter(
            pet_registry=SimpleNamespace(),
            household=SimpleNamespace(relationships=relationships),
        )

        self.assertTrue(
            adapter.apply_relationship_reward(
                "Tokai Teio",
                "Symboli Rudolf",
                {"trust": 1},
                20.0,
            )
        )
        relationships.apply_delta.assert_called_once_with(
            actor_name="Tokai Teio",
            target_name="Symboli Rudolf",
            relation_delta={"trust": 1},
            updated_at=20.0,
        )


class GameplayAppAdapterTests(unittest.TestCase):
    def test_activity_and_transformation_calls_use_owned_controllers(self):
        runtime = GameplayAppAdapterMixin()
        runtime.activity_runtime_controller = SimpleNamespace(
            update_work=Mock(return_value=True),
        )
        runtime.transformation_runtime_controller = SimpleNamespace(
            get_preview_state=Mock(return_value={"current_form": "base"}),
        )

        self.assertTrue(runtime.update_rudolf_work(now=10.0))
        self.assertEqual(
            runtime.get_transformation_preview_state("Tokai Teio"),
            {"current_form": "base"},
        )
        runtime.activity_runtime_controller.update_work.assert_called_once_with(
            now=10.0
        )
        runtime.transformation_runtime_controller.get_preview_state.assert_called_once_with(
            "Tokai Teio"
        )


class HouseholdAppAdapterTests(unittest.TestCase):
    def test_queries_and_persistence_use_owned_coordinators(self):
        runtime = HouseholdAppAdapterMixin()
        runtime.household_coordinator = SimpleNamespace(
            recent_events=Mock(return_value=("event",)),
        )
        runtime.runtime_persistence_coordinator = SimpleNamespace(
            capture_state=Mock(return_value={"household": {}}),
        )

        self.assertEqual(runtime.recent_household_events(5), ("event",))
        self.assertEqual(
            runtime.capture_household_persistence_state(),
            {"household": {}},
        )
        runtime.household_coordinator.recent_events.assert_called_once_with(
            limit=5
        )
        runtime.runtime_persistence_coordinator.capture_state.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
