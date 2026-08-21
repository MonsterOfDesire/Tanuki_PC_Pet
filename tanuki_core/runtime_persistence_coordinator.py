class RuntimePersistenceCoordinator:
    """Aggregates household and achievement state without duplicating either."""

    def __init__(
        self,
        *,
        household_coordinator,
        achievement_runtime_coordinator,
        dashboard,
    ):
        self.household_coordinator = household_coordinator
        self.achievement_runtime_coordinator = (
            achievement_runtime_coordinator
        )
        self.dashboard = dashboard

    def capture_state(self):
        payload = self.household_coordinator.capture_persistence_state()
        payload["achievements"] = (
            self.achievement_runtime_coordinator.capture_persistence_state()
        )
        return payload

    def apply_state(self, payload):
        applied = self.household_coordinator.apply_persistence_state(
            payload,
            dashboard=self.dashboard,
        )
        achievement_payload = (
            payload.get("achievements")
            if isinstance(payload, dict)
            else None
        )
        if isinstance(achievement_payload, dict):
            self.achievement_runtime_coordinator.apply_persistence_state(
                achievement_payload
            )
        return applied
