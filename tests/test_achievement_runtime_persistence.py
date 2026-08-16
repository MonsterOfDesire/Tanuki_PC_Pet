import unittest
from types import SimpleNamespace

from tanuki_core.achievement_runtime_coordinator import (
    AchievementRuntimeCoordinator,
)
from tanuki_core.achievement_state import AchievementState
from tanuki_core.app_runtime import TanukiAppRuntime
from tanuki_core.runtime_persistence_coordinator import (
    RuntimePersistenceCoordinator,
)


class FakeHouseholdCoordinator:
    def __init__(self):
        self.applied_payload = None

    def capture_persistence_state(self):
        return {"living_fund": 500}

    def apply_persistence_state(self, payload, *, dashboard=None):
        self.applied_payload = payload
        return True


class AchievementRuntimePersistenceTests(unittest.TestCase):
    def test_runtime_embeds_achievement_state_in_household_config(self):
        coordinator = FakeHouseholdCoordinator()
        achievement_state = AchievementState()
        achievement_state.progress_for(
            "sandbox",
            "race.first_natural_finish",
        ).unlock(12.0)
        achievement_state.mark_event_processed("sandbox", "race-1")
        persistence = _persistence_coordinator(
            coordinator,
            achievement_state,
        )
        runtime = SimpleNamespace(
            runtime_persistence_coordinator=persistence,
        )

        payload = TanukiAppRuntime.capture_household_persistence_state(runtime)

        self.assertEqual(payload["living_fund"], 500)
        self.assertIn("achievements", payload)
        self.assertEqual(
            payload["achievements"]["progress_by_world_mode"]["sandbox"]
            ["race.first_natural_finish"]["unlocked_at"],
            12.0,
        )

    def test_runtime_restores_achievement_state_without_affecting_household_apply(self):
        coordinator = FakeHouseholdCoordinator()
        achievement_state = AchievementState()
        persistence = _persistence_coordinator(
            coordinator,
            achievement_state,
        )
        runtime = SimpleNamespace(
            runtime_persistence_coordinator=persistence,
        )
        payload = {
            "living_fund": 700,
            "achievements": {
                "achievement_schema_version": 1,
                "progress_by_world_mode": {
                    "sandbox": {
                        "race.first_natural_finish": {
                            "count": 1,
                            "observed_keys": [],
                            "observed_event_names": [],
                            "unlocked_at": 22.0,
                            "completion_count": 1,
                            "updated_at": 22.0,
                        }
                    }
                },
                "processed_event_ids": {
                    "sandbox": ["race-1"],
                    "golden_legend": [],
                },
            },
        }

        applied = TanukiAppRuntime.apply_household_persistence_state(
            runtime,
            payload,
        )

        self.assertTrue(applied)
        self.assertIs(coordinator.applied_payload, payload)
        self.assertTrue(
            achievement_state.is_unlocked(
                "sandbox",
                "race.first_natural_finish",
            )
        )
        self.assertTrue(
            achievement_state.has_processed_event("sandbox", "race-1")
        )


def _persistence_coordinator(household_coordinator, achievement_state):
    achievement_coordinator = AchievementRuntimeCoordinator(
        state=achievement_state,
        eligibility_guard=SimpleNamespace(),
        time_scale_provider=lambda: 1.0,
        world_mode_provider=lambda: "sandbox",
        service=SimpleNamespace(),
        gameplay_bridge=SimpleNamespace(),
    )
    return RuntimePersistenceCoordinator(
        household_coordinator=household_coordinator,
        achievement_runtime_coordinator=achievement_coordinator,
        dashboard=object(),
    )


if __name__ == "__main__":
    unittest.main()
