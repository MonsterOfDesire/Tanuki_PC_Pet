import unittest
from types import SimpleNamespace

from tanuki_core.runtime_persistence_coordinator import (
    RuntimePersistenceCoordinator,
)


class RuntimePersistenceCoordinatorTests(unittest.TestCase):
    def test_missing_achievement_section_preserves_household_apply_result(self):
        household = SimpleNamespace(
            capture_persistence_state=lambda: {"living_fund": 100},
            apply_persistence_state=lambda payload, dashboard=None: (
                payload,
                dashboard,
            ),
        )
        achievement_calls = []
        achievements = SimpleNamespace(
            capture_persistence_state=lambda: {"version": 1},
            apply_persistence_state=lambda payload: achievement_calls.append(
                payload
            ),
        )
        coordinator = RuntimePersistenceCoordinator(
            household_coordinator=household,
            achievement_runtime_coordinator=achievements,
            dashboard="dashboard",
        )

        captured = coordinator.capture_state()
        applied = coordinator.apply_state({"living_fund": 200})

        self.assertEqual(
            captured,
            {"living_fund": 100, "achievements": {"version": 1}},
        )
        self.assertEqual(applied, ({"living_fund": 200}, "dashboard"))
        self.assertEqual(achievement_calls, [])


if __name__ == "__main__":
    unittest.main()
