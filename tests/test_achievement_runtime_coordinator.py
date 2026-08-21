import unittest
from types import SimpleNamespace

from tanuki_core.achievement_gameplay_bridge import AchievementGameplayBridge
from tanuki_core.achievement_runtime_coordinator import (
    AchievementRuntimeCoordinator,
)


class FakeAchievementService:
    def __init__(self):
        self.started = []
        self.cancelled = []
        self.consumed = []

    def begin_activity_session(self, **fields):
        self.started.append(fields)
        return True

    def cancel_activity_session(self, activity_id, *, reason):
        self.cancelled.append((activity_id, reason))
        return True

    def consume_activity_metadata(self, metadata):
        self.consumed.append(dict(metadata))
        return "consumed"


class AchievementRuntimeCoordinatorTests(unittest.TestCase):
    def build_coordinator(self, *, callbacks=None):
        service = FakeAchievementService()
        if callbacks is None:
            callbacks = []
        bridge = AchievementGameplayBridge(
            service=service,
            world_mode_provider=lambda: "sandbox",
        )
        coordinator = AchievementRuntimeCoordinator(
            state=None,
            eligibility_guard=SimpleNamespace(),
            time_scale_provider=lambda: 1.0,
            world_mode_provider=lambda: "sandbox",
            service=service,
            gameplay_bridge=bridge,
            save_callback=lambda: callbacks.append("save"),
            unlock_callback=lambda ids: callbacks.append(tuple(ids)),
        )
        return coordinator, service

    def test_state_change_saves_and_only_notifies_real_unlocks(self):
        callbacks = []
        coordinator, _service = self.build_coordinator(
            callbacks=callbacks
        )

        coordinator.handle_state_changed(
            SimpleNamespace(unlocked_achievement_ids=())
        )
        coordinator.handle_state_changed(
            SimpleNamespace(unlocked_achievement_ids=("race.first",))
        )

        self.assertEqual(callbacks, ["save", "save", ("race.first",)])

    def test_activity_session_is_resolved_from_activity_coordinator(self):
        coordinator, service = self.build_coordinator()
        activity = SimpleNamespace(
            activity_id="race-1",
            source="autonomous",
            started_at=12.0,
            metadata={
                "world_mode": "sandbox",
                "execution_mode": "autonomous",
            },
        )
        activities = SimpleNamespace(
            get_activity=lambda activity_id: (
                activity if activity_id == "race-1" else None
            )
        )

        handled = coordinator.begin_activity_session(
            "race-1",
            activity_coordinator=activities,
            world_mode="golden_legend",
        )

        self.assertTrue(handled)
        self.assertEqual(
            service.started,
            [
                {
                    "activity_id": "race-1",
                    "world_mode": "sandbox",
                    "source": "autonomous",
                    "execution_mode": "autonomous",
                    "started_at": 12.0,
                }
            ],
        )

    def test_payload_gate_ignores_noncanonical_metadata(self):
        coordinator, service = self.build_coordinator()

        self.assertIsNone(coordinator.consume_payload({"source": "test"}))
        result = coordinator.consume_payload(
            {"activity_event_name": "race.completed", "event_id": "r1"}
        )

        self.assertEqual(result, "consumed")
        self.assertEqual(len(service.consumed), 1)


if __name__ == "__main__":
    unittest.main()
