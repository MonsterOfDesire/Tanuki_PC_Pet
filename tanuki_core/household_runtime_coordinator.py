from __future__ import annotations

import time
from dataclasses import dataclass

from .household_event_rules import (
    HouseholdEventScheduleState,
    build_household_event_schedule,
    refresh_household_summary_if_needed,
    resolve_household_events,
)
from .household_persistence import (
    apply_household_persistence_state,
    capture_household_persistence_state,
)
from .household_state import (
    HouseholdEventLog,
    HouseholdState,
    record_household_event,
    record_player_donate_household_fund,
)
from .runtime import app_now


@dataclass
class HouseholdRuntimeCoordinator:
    household: HouseholdState
    event_log: HouseholdEventLog
    event_schedule: HouseholdEventScheduleState

    @staticmethod
    def household_entry_affects_summary(entry) -> bool:
        if not entry:
            return False
        if getattr(entry, "living_fund_delta", 0):
            return True
        if float(getattr(entry, "household_pressure_delta", 0.0) or 0.0):
            return True
        channel = str(getattr(entry, "channel", "") or "")
        category = str(getattr(entry, "category", "") or "")
        if channel == "social" or category in {"social", "care", "relationship"}:
            return False
        return channel in {"economy", "item", "story", "system"} or category in {
            "household",
            "economy",
            "player_help",
            "player_offer",
            "item",
            "system",
        }

    def refresh_dashboard_views_for_entry(self, dashboard, entry) -> None:
        if dashboard is None:
            return
        if (
            self.household_entry_affects_summary(entry)
            and hasattr(dashboard, "refresh_household_summary_if_open")
        ):
            dashboard.refresh_household_summary_if_open()
        if hasattr(dashboard, "refresh_social_log_if_open"):
            dashboard.refresh_social_log_if_open()
        if (
            getattr(entry, "relation_delta", {})
            and hasattr(dashboard, "refresh_relationship_table_if_open")
        ):
            dashboard.refresh_relationship_table_if_open()

    @staticmethod
    def notify_household_log_icon(pets, entry) -> bool:
        candidate_names = []
        actor_name = str(getattr(entry, "actor_name", "") or "")
        target_name = str(getattr(entry, "target_name", "") or "")
        if actor_name and actor_name != "Player":
            candidate_names.append(actor_name)
        if target_name and target_name not in candidate_names:
            candidate_names.append(target_name)

        pet_by_name = {
            str(getattr(pet, "name", "") or ""): pet
            for pet in pets or ()
            if getattr(pet, "isVisible", lambda: False)()
        }
        for pet_name in candidate_names:
            pet = pet_by_name.get(pet_name)
            if pet is None:
                continue
            pop_log_icon = getattr(pet, "pop_log_icon", None)
            if callable(pop_log_icon):
                pop_log_icon()
                return True
        return False

    def record_event(
        self,
        *,
        dashboard=None,
        pets=(),
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
        entry = record_household_event(
            self.household,
            self.event_log,
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
        self.notify_household_log_icon(pets, entry)
        self.refresh_dashboard_views_for_entry(dashboard, entry)
        return entry

    def recent_events(self, limit=10):
        return self.event_log.recent_entries(limit=limit)

    def query_events(self, **filters):
        return self.event_log.query_entries(**filters)

    def relationship_entries_for(self, actor_name):
        return self.household.relationships.entries_for_actor(actor_name)

    def all_relationship_entries(self):
        return self.household.relationships.all_entries()

    def donate_household_fund(self, *, world_mode, amount=100, actor_name="Player", now=None):
        if world_mode != "golden_legend":
            return None
        now = app_now() if now is None else float(now)
        return record_player_donate_household_fund(
            self.household,
            self.event_log,
            occurred_at=now,
            amount=amount,
            actor_name=actor_name,
        )

    def collect_pending_social_log_events(self, *, pets, dashboard=None, now=None):
        now = app_now() if now is None else float(now)
        entries = []
        for pet in pets or ():
            payload = dict(getattr(pet, "pending_social_log_event", {}) or {})
            if not payload:
                continue
            pet.pending_social_log_event = {}
            actor_name = str(payload.get("actor_name", "") or "").strip()
            target_name = str(payload.get("target_name", "") or "").strip()
            summary = str(payload.get("summary", "") or "").strip()
            if not actor_name or not target_name or not summary:
                continue
            entry = self.record_event(
                dashboard=dashboard,
                pets=pets,
                occurred_at=float(payload.get("occurred_at", now) or now),
                category="social",
                event_type=str(payload.get("event_type", "observe_social_log") or "observe_social_log"),
                channel="social",
                importance=str(payload.get("importance", "low") or "low"),
                summary=summary,
                actor_name=actor_name,
                target_name=target_name,
                relation_delta=dict(payload.get("relation_delta", {}) or {}),
                tags=tuple(payload.get("tags", ()) or ()),
                metadata=dict(payload.get("metadata", {}) or {}),
                apply_deltas=True,
            )
            entries.append(entry)
        return entries

    def update_events(self, *, world_mode, pets, dashboard, profiler, now=None):
        profiler_started_at = time.perf_counter()
        now = app_now() if now is None else float(now)
        recorded_social_events = self.collect_pending_social_log_events(
            pets=pets,
            dashboard=dashboard,
            now=now,
        )
        if world_mode != "golden_legend":
            refresh_household_summary_if_needed(dashboard, recorded_social_events)
            profiler.record_section(
                "household.update",
                (time.perf_counter() - profiler_started_at) * 1000.0,
            )
            return recorded_social_events

        resolved_events = resolve_household_events(
            self.household,
            self.event_schedule,
            now=now,
        )
        for event in resolved_events:
            self.record_event(
                dashboard=dashboard,
                pets=pets,
                occurred_at=event.occurred_at,
                category=event.category,
                event_type=event.event_type,
                channel=event.channel,
                importance=event.importance,
                summary=event.summary,
                actor_name=event.actor_name,
                target_name=event.target_name,
                mood_delta=event.mood_delta,
                relation_delta=event.relation_delta,
                tags=event.tags,
                living_fund_delta=event.living_fund_delta,
                household_pressure_delta=event.household_pressure_delta,
                metadata=event.metadata,
            )
        all_events = [*recorded_social_events, *resolved_events]
        refresh_household_summary_if_needed(dashboard, all_events)
        profiler.record_section(
            "household.update",
            (time.perf_counter() - profiler_started_at) * 1000.0,
        )
        return all_events

    def capture_persistence_state(self):
        return capture_household_persistence_state(
            self.household,
            self.event_log,
            self.event_schedule,
        )

    def apply_persistence_state(self, payload, *, dashboard=None):
        applied = apply_household_persistence_state(
            payload,
            self.household,
            self.event_log,
            self.event_schedule,
        )
        if applied and dashboard is not None:
            dashboard.refresh_household_summary_if_open()
        return applied

    def reset_event_schedule(self, now=None):
        now = app_now() if now is None else float(now)
        replacement = build_household_event_schedule(now)
        self.event_schedule.next_teio_drink_at = replacement.next_teio_drink_at
        self.event_schedule.next_rudolf_work_at = replacement.next_rudolf_work_at
        self.event_schedule.next_rudolf_collectible_at = replacement.next_rudolf_collectible_at
        return self.event_schedule

    def handle_world_mode_change(
        self,
        world_mode,
        *,
        previous_mode=None,
        dashboard=None,
        clear_offer_scene,
        clear_offer_hover,
        now=None,
    ) -> bool:
        if world_mode == previous_mode:
            return False
        if world_mode == "golden_legend":
            self.reset_event_schedule(now)
        clear_offer_scene()
        clear_offer_hover()
        if dashboard is not None:
            dashboard.refresh_household_summary_if_open()
        return True
