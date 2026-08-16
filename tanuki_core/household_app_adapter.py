from __future__ import annotations

from .runtime import app_now


class HouseholdAppAdapterMixin:
    """Compatibility surface for household queries, events and persistence."""

    def record_household_event(
        self,
        *,
        occurred_at: float,
        category: str = "system",
        event_type: str = "info",
        channel: str = "",
        importance: str = "normal",
        summary: str = "",
        actor_name: str = "",
        target_name: str = "",
        mood_delta: float = 0.0,
        relation_delta: dict[str, float] | None = None,
        tags=(),
        living_fund_delta: int = 0,
        household_pressure_delta: float = 0.0,
        metadata: dict[str, object] | None = None,
        apply_deltas: bool = True,
    ):
        return self.household_event_gateway.record_event(
            occurred_at=occurred_at,
            category=category,
            event_type=event_type,
            channel=channel,
            importance=importance,
            summary=summary,
            actor_name=actor_name,
            target_name=target_name,
            mood_delta=mood_delta,
            relation_delta=relation_delta,
            tags=tags,
            living_fund_delta=living_fund_delta,
            household_pressure_delta=household_pressure_delta,
            metadata=metadata,
            apply_deltas=apply_deltas,
        )

    def _record_resolved_household_event(self, event):
        return self.household_event_gateway.record_resolved_event(event)

    def _consume_achievement_metadata(self, entry):
        coordinator = getattr(self, "achievement_runtime_coordinator", None)
        if coordinator is None:
            return None
        return coordinator.consume_entry(entry)

    def _consume_achievement_payload(
        self,
        metadata,
        *,
        instantaneous=False,
    ):
        coordinator = getattr(self, "achievement_runtime_coordinator", None)
        if coordinator is None:
            return None
        return coordinator.consume_payload(
            metadata,
            instantaneous=instantaneous,
        )

    def _handle_achievement_state_changed(self, result):
        return self.achievement_runtime_coordinator.handle_state_changed(result)

    def refresh_dashboard_views_for_household_entry(self, entry):
        return self.household_coordinator.refresh_dashboard_views_for_entry(
            self.dashboard,
            entry,
        )

    def household_entry_affects_summary(self, entry):
        return self.household_coordinator.household_entry_affects_summary(entry)

    def notify_household_log_icon(self, entry):
        return self.household_coordinator.notify_household_log_icon(
            self.pets_list,
            entry,
        )

    def recent_household_events(self, limit=10):
        return self.household_coordinator.recent_events(limit=limit)

    def query_household_events(self, **filters):
        return self.household_coordinator.query_events(**filters)

    def household_relationship_entries_for(self, actor_name):
        return self.household_coordinator.relationship_entries_for(actor_name)

    def all_household_relationship_entries(self):
        return self.household_coordinator.all_relationship_entries()

    def donate_household_fund(self, amount=100, actor_name="Player"):
        return self.household_coordinator.donate_household_fund(
            world_mode=self.settings_provider.world_mode,
            amount=amount,
            actor_name=actor_name,
        )

    def collect_pending_social_log_events(self, now=None):
        return self.household_coordinator.collect_pending_social_log_events(
            pets=self.pets_list,
            dashboard=self.dashboard,
            now=now,
        )

    def update_household_events(self, now=None):
        now = app_now() if now is None else float(now)
        self.update_rudolf_work(now=now)
        self.update_sleep(now=now)
        entries = self.household_coordinator.update_events(
            world_mode=self.settings_provider.world_mode,
            pets=self.pets_list,
            dashboard=self.dashboard,
            profiler=self.profiler,
            now=now,
        )
        return self.household_event_gateway.process_entries(
            entries,
            occurred_at=now,
        )

    def capture_household_persistence_state(self):
        return self.runtime_persistence_coordinator.capture_state()

    def apply_household_persistence_state(self, payload):
        return self.runtime_persistence_coordinator.apply_state(payload)

    def handle_world_mode_change(self, world_mode, previous_mode=None):
        self.activity_runtime_controller.handle_world_mode_change(
            world_mode,
            previous_mode=previous_mode,
        )
        return self.household_coordinator.handle_world_mode_change(
            world_mode,
            previous_mode=previous_mode,
            dashboard=self.dashboard,
            clear_offer_scene=self.clear_offer_scene,
            clear_offer_hover=lambda: self.clear_offer_hover(
                apply_miss=False
            ),
        )
