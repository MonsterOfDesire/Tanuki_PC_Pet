from .household_event_rules import HouseholdEventScheduleState
from .household_state import (
    HouseholdEventLog,
    HouseholdEventLogEntry,
    HouseholdRelationshipEntry,
    HouseholdState,
    clamp_household_pressure,
    clamp_relationship_metric,
    normalize_event_tags,
    normalize_relation_delta,
    resolve_event_channel,
)
from .race_state import RaceCharacterStatistics


PERSISTED_HOUSEHOLD_LOG_LIMIT = 32


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def capture_household_persistence_state(
    household: HouseholdState,
    event_log: HouseholdEventLog,
    event_schedule: HouseholdEventScheduleState,
    *,
    log_limit: int = PERSISTED_HOUSEHOLD_LOG_LIMIT,
) -> dict:
    entries = event_log.recent_entries(limit=log_limit)
    return {
        "living_fund": int(household.living_fund),
        "household_pressure": float(household.household_pressure),
        "relationship_ledger": [
            household_relationship_entry_to_payload(entry)
            for entry in household.relationships.all_entries()
        ],
        "race_statistics": {
            "entries": [
                race_statistics_entry_to_payload(entry)
                for entry in sorted(
                    household.race_statistics.entries.values(),
                    key=lambda item: item.character_name,
                )
            ],
            "processed_activity_ids": sorted(
                household.race_statistics.processed_activity_ids
            ),
        },
        "event_log_next_sequence": int(event_log.next_sequence),
        "event_log": [household_event_entry_to_payload(entry) for entry in entries],
        "event_schedule": {
            "next_teio_drink_at": float(event_schedule.next_teio_drink_at),
            "next_rudolf_work_at": float(event_schedule.next_rudolf_work_at),
            "next_rudolf_collectible_at": float(event_schedule.next_rudolf_collectible_at),
        },
    }


def household_event_entry_to_payload(entry: HouseholdEventLogEntry) -> dict:
    return {
        "sequence": int(entry.sequence),
        "occurred_at": float(entry.occurred_at),
        "wall_clock_time": float(entry.wall_clock_time),
        "category": str(entry.category),
        "event_type": str(entry.event_type),
        "channel": str(entry.channel),
        "importance": str(entry.importance),
        "summary": str(entry.summary),
        "actor_name": str(entry.actor_name),
        "target_name": str(entry.target_name),
        "mood_delta": float(entry.mood_delta),
        "relation_delta": dict(entry.relation_delta),
        "tags": list(entry.tags),
        "living_fund_delta": int(entry.living_fund_delta),
        "household_pressure_delta": float(entry.household_pressure_delta),
        "metadata": dict(entry.metadata),
    }


def household_relationship_entry_to_payload(entry: HouseholdRelationshipEntry) -> dict:
    return {
        "actor_name": str(entry.actor_name),
        "target_name": str(entry.target_name),
        "familiarity": float(entry.familiarity),
        "trust": float(entry.trust),
        "attachment": float(entry.attachment),
        "tension": float(entry.tension),
        "updated_at": float(entry.updated_at),
        "event_count": int(entry.event_count),
    }


def race_statistics_entry_to_payload(entry: RaceCharacterStatistics) -> dict:
    return {
        "character_name": str(entry.character_name),
        "completed_races": int(entry.completed_races),
        "wins": int(entry.wins),
        "losses": int(entry.losses),
        "golden_races": int(entry.golden_races),
        "sandbox_races": int(entry.sandbox_races),
        "autonomous_races": int(entry.autonomous_races),
        "manual_races": int(entry.manual_races),
    }


def apply_household_persistence_state(
    payload: dict,
    household: HouseholdState,
    event_log: HouseholdEventLog,
    event_schedule: HouseholdEventScheduleState,
) -> bool:
    if not isinstance(payload, dict):
        return False

    household.living_fund = max(0, _safe_int(payload.get("living_fund"), household.living_fund))
    household.household_pressure = clamp_household_pressure(
        _safe_float(payload.get("household_pressure"), household.household_pressure)
    )

    _restore_household_relationships(payload.get("relationship_ledger", []), household)
    _restore_race_statistics(payload.get("race_statistics", {}), household)
    _restore_household_event_log(payload.get("event_log", []), payload.get("event_log_next_sequence"), event_log)
    _restore_household_event_schedule(payload.get("event_schedule", {}), event_schedule)
    return True


def _restore_household_event_log(raw_entries, raw_next_sequence, event_log: HouseholdEventLog) -> None:
    event_log.entries.clear()
    event_log.next_sequence = 1
    if isinstance(raw_entries, list):
        for raw_entry in raw_entries:
            if not isinstance(raw_entry, dict):
                continue
            event_log.append(
                HouseholdEventLogEntry(
                    sequence=max(1, _safe_int(raw_entry.get("sequence"), event_log.next_sequence)),
                    occurred_at=_safe_float(raw_entry.get("occurred_at"), 0.0),
                    wall_clock_time=_safe_float(raw_entry.get("wall_clock_time"), 0.0),
                    category=str(raw_entry.get("category", "system")),
                    event_type=str(raw_entry.get("event_type", "info")),
                    channel=resolve_event_channel(
                        raw_entry.get("channel", ""),
                        str(raw_entry.get("category", "system")),
                    ),
                    importance=str(raw_entry.get("importance", "normal") or "normal").strip() or "normal",
                    summary=str(raw_entry.get("summary", "")),
                    actor_name=str(raw_entry.get("actor_name", "")),
                    target_name=str(raw_entry.get("target_name", "")),
                    mood_delta=_safe_float(raw_entry.get("mood_delta"), 0.0),
                    relation_delta=normalize_relation_delta(raw_entry.get("relation_delta", {})),
                    tags=normalize_event_tags(raw_entry.get("tags", ())),
                    living_fund_delta=_safe_int(raw_entry.get("living_fund_delta"), 0),
                    household_pressure_delta=_safe_float(raw_entry.get("household_pressure_delta"), 0.0),
                    metadata=dict(raw_entry.get("metadata", {}))
                    if isinstance(raw_entry.get("metadata", {}), dict)
                    else {},
                )
            )

    next_sequence = max(1, _safe_int(raw_next_sequence, event_log.next_sequence))
    event_log.next_sequence = max(next_sequence, event_log.next_sequence)


def _restore_household_relationships(raw_entries, household: HouseholdState) -> None:
    household.relationships.clear()
    if not isinstance(raw_entries, list):
        return
    for raw_entry in raw_entries:
        if not isinstance(raw_entry, dict):
            continue
        household.relationships.upsert_entry(
            HouseholdRelationshipEntry(
                actor_name=str(raw_entry.get("actor_name", "")),
                target_name=str(raw_entry.get("target_name", "")),
                familiarity=clamp_relationship_metric(_safe_float(raw_entry.get("familiarity"), 0.0)),
                trust=clamp_relationship_metric(_safe_float(raw_entry.get("trust"), 0.0)),
                attachment=clamp_relationship_metric(_safe_float(raw_entry.get("attachment"), 0.0)),
                tension=clamp_relationship_metric(_safe_float(raw_entry.get("tension"), 0.0)),
                updated_at=_safe_float(raw_entry.get("updated_at"), 0.0),
                event_count=max(0, _safe_int(raw_entry.get("event_count"), 0)),
            )
        )


def _restore_race_statistics(raw_statistics, household: HouseholdState) -> None:
    ledger = household.race_statistics
    ledger.clear()
    if not isinstance(raw_statistics, dict):
        return
    raw_entries = raw_statistics.get("entries", [])
    if isinstance(raw_entries, list):
        for raw_entry in raw_entries:
            if not isinstance(raw_entry, dict):
                continue
            character_name = str(raw_entry.get("character_name", "")).strip()
            if not character_name:
                continue
            ledger.entries[character_name] = RaceCharacterStatistics(
                character_name=character_name,
                completed_races=max(0, _safe_int(raw_entry.get("completed_races"), 0)),
                wins=max(0, _safe_int(raw_entry.get("wins"), 0)),
                losses=max(0, _safe_int(raw_entry.get("losses"), 0)),
                golden_races=max(0, _safe_int(raw_entry.get("golden_races"), 0)),
                sandbox_races=max(0, _safe_int(raw_entry.get("sandbox_races"), 0)),
                autonomous_races=max(0, _safe_int(raw_entry.get("autonomous_races"), 0)),
                manual_races=max(0, _safe_int(raw_entry.get("manual_races"), 0)),
            )
    raw_activity_ids = raw_statistics.get("processed_activity_ids", [])
    if isinstance(raw_activity_ids, list):
        ledger.processed_activity_ids.update(
            str(activity_id).strip()
            for activity_id in raw_activity_ids
            if str(activity_id).strip()
        )


def _restore_household_event_schedule(raw_schedule, event_schedule: HouseholdEventScheduleState) -> None:
    if not isinstance(raw_schedule, dict):
        return
    event_schedule.next_teio_drink_at = _safe_float(
        raw_schedule.get("next_teio_drink_at"),
        event_schedule.next_teio_drink_at,
    )
    event_schedule.next_rudolf_work_at = _safe_float(
        raw_schedule.get("next_rudolf_work_at"),
        event_schedule.next_rudolf_work_at,
    )
    event_schedule.next_rudolf_collectible_at = _safe_float(
        raw_schedule.get("next_rudolf_collectible_at"),
        event_schedule.next_rudolf_collectible_at,
    )
