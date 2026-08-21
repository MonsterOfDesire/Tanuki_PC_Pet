from .runtime import app_now


class HouseholdEventGateway:
    """Records household events and runs their application-level observers."""

    def __init__(
        self,
        *,
        household_coordinator,
        dashboard,
        pets,
        transformation_tendency_coordinator,
        transformation_executor,
        achievement_runtime_coordinator,
        now_provider=app_now,
    ):
        self.household_coordinator = household_coordinator
        self.dashboard = dashboard
        self.pets = pets
        self.transformation_tendency_coordinator = (
            transformation_tendency_coordinator
        )
        self.transformation_executor = transformation_executor
        self.achievement_runtime_coordinator = (
            achievement_runtime_coordinator
        )
        self.now_provider = now_provider

    def record_event(self, **event_fields):
        entry = self.household_coordinator.record_event(
            dashboard=self.dashboard,
            pets=self.pets,
            **event_fields,
        )
        self.process_entry(
            entry,
            occurred_at=float(event_fields.get("occurred_at", self.now_provider())),
        )
        return entry

    def record_resolved_event(self, event):
        entry = self.household_coordinator.record_resolved_event(
            event,
            dashboard=self.dashboard,
            pets=self.pets,
        )
        self.process_entry(
            entry,
            occurred_at=float(
                getattr(event, "occurred_at", self.now_provider())
            ),
        )
        return entry

    def process_entry(self, entry, *, occurred_at):
        if self.transformation_tendency_coordinator is not None:
            self.transformation_tendency_coordinator.process_household_entry(
                entry,
                pets=self.pets,
                executor=self.transformation_executor,
                now=float(occurred_at),
            )
        if self.achievement_runtime_coordinator is not None:
            self.achievement_runtime_coordinator.consume_entry(entry)

    def process_entries(self, entries, *, occurred_at):
        for entry in tuple(entries or ()):
            self.process_entry(entry, occurred_at=float(occurred_at))
        return entries
