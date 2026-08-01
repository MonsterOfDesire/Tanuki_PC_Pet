from dataclasses import dataclass, field

from .household_state import HouseholdState
from .rudolf_work_rules import (
    WORK_LIVING_FUND_THRESHOLD,
    WORK_PRESSURE_THRESHOLD,
)


TEIO_DRINK_INTERVAL_SECONDS = 30.0
RUDOLF_WORK_INTERVAL_SECONDS = 55.0
RUDOLF_COLLECTIBLE_INTERVAL_SECONDS = 85.0

TEIO_DRINK_COST = 18
RUDOLF_COLLECTIBLE_COST = 35

TEIO_DRINK_PRESSURE = 4.0
RUDOLF_COLLECTIBLE_PRESSURE = 3.0

COLLECTIBLE_LIVING_FUND_THRESHOLD = 960
COLLECTIBLE_PRESSURE_MAX = 38.0


@dataclass
class HouseholdEventScheduleState:
    next_teio_drink_at: float = 0.0
    next_rudolf_work_at: float = 0.0
    next_rudolf_collectible_at: float = 0.0


@dataclass(frozen=True)
class HouseholdResolvedEvent:
    occurred_at: float
    category: str
    event_type: str
    summary: str
    channel: str = ""
    importance: str = "normal"
    actor_name: str = ""
    target_name: str = ""
    mood_delta: float = 0.0
    relation_delta: dict[str, float] = field(default_factory=dict)
    tags: tuple[str, ...] = field(default_factory=tuple)
    living_fund_delta: int = 0
    household_pressure_delta: float = 0.0
    metadata: dict[str, object] = field(default_factory=dict)


def build_household_event_schedule(now: float = 0.0) -> HouseholdEventScheduleState:
    return HouseholdEventScheduleState(
        next_teio_drink_at=now + TEIO_DRINK_INTERVAL_SECONDS,
        next_rudolf_work_at=now + RUDOLF_WORK_INTERVAL_SECONDS,
        next_rudolf_collectible_at=now + RUDOLF_COLLECTIBLE_INTERVAL_SECONDS,
    )


def _build_teio_drink_event(now: float) -> HouseholdResolvedEvent:
    return HouseholdResolvedEvent(
        occurred_at=now,
        category="economy",
        event_type="teio_drink_expense",
        summary="帝寶又偷偷買了飲料。",
        actor_name="Tokai Teio",
        living_fund_delta=-TEIO_DRINK_COST,
        household_pressure_delta=TEIO_DRINK_PRESSURE,
        metadata={"source": "periodic_household_event"},
    )


def consume_rudolf_work_schedule_if_due(
    schedule: HouseholdEventScheduleState,
    *,
    now: float,
) -> bool:
    if float(now) < float(schedule.next_rudolf_work_at):
        return False
    schedule.next_rudolf_work_at = (
        float(now) + RUDOLF_WORK_INTERVAL_SECONDS
    )
    return True


def _should_trigger_rudolf_collectible(household: HouseholdState) -> bool:
    return (
        household.living_fund >= COLLECTIBLE_LIVING_FUND_THRESHOLD
        and household.household_pressure <= COLLECTIBLE_PRESSURE_MAX
    )


def _build_rudolf_collectible_event(now: float) -> HouseholdResolvedEvent:
    return HouseholdResolvedEvent(
        occurred_at=now,
        category="economy",
        event_type="rudolf_collectible_expense",
        summary="魯道夫忍不住添購了一件收藏品。",
        actor_name="Symboli Rudolf",
        living_fund_delta=-RUDOLF_COLLECTIBLE_COST,
        household_pressure_delta=RUDOLF_COLLECTIBLE_PRESSURE,
        metadata={"source": "periodic_household_event"},
    )


def resolve_household_events(
    household: HouseholdState,
    schedule: HouseholdEventScheduleState,
    *,
    now: float,
) -> list[HouseholdResolvedEvent]:
    events: list[HouseholdResolvedEvent] = []

    if now >= schedule.next_teio_drink_at:
        schedule.next_teio_drink_at = now + TEIO_DRINK_INTERVAL_SECONDS
        events.append(_build_teio_drink_event(now))

    if now >= schedule.next_rudolf_collectible_at:
        schedule.next_rudolf_collectible_at = now + RUDOLF_COLLECTIBLE_INTERVAL_SECONDS
        if _should_trigger_rudolf_collectible(household):
            events.append(_build_rudolf_collectible_event(now))

    return events


def refresh_household_summary_if_needed(dashboard, resolved_events) -> bool:
    refreshed = False
    if resolved_events and hasattr(dashboard, "refresh_household_summary_if_open"):
        dashboard.refresh_household_summary_if_open()
        refreshed = True
    if resolved_events and hasattr(dashboard, "refresh_social_log_if_open"):
        dashboard.refresh_social_log_if_open()
        refreshed = True
    if resolved_events and hasattr(dashboard, "refresh_relationship_table_if_open"):
        dashboard.refresh_relationship_table_if_open()
        refreshed = True
    return refreshed
