from __future__ import annotations

from collections.abc import Iterable, Mapping


ACTIVITY_EVENT_PAYLOAD_SCHEMA_VERSION = 1

ACTIVITY_EVENT_WORK_COMPLETED = "activity.work.completed"
ACTIVITY_EVENT_RACE_COMPLETED = "activity.race.completed"
ACTIVITY_EVENT_RACE_DECLINED = "activity.race.declined"
ACTIVITY_EVENT_CHORUS_COMPLETED = "activity.chorus.completed"
ACTIVITY_EVENT_CHORUS_INTERRUPTED = "activity.chorus.interrupted"
ACTIVITY_EVENT_SLEEP_STARTED = "activity.sleep.started"
ACTIVITY_EVENT_SLEEP_COMPLETED = "activity.sleep.completed"
ACTIVITY_EVENT_SLEEP_INTERRUPTED = "activity.sleep.interrupted"
ACTIVITY_EVENT_SLEEP_GROUP_JOINED = "activity.sleep.group_joined"
ACTIVITY_EVENT_TRANSFORMATION_COMPLETED = (
    "activity.transformation.completed"
)
INTERACTION_EVENT_CARE_COMPLETED = "interaction.care.completed"
INTERACTION_EVENT_HONEY_GUARD_COMPLETED = (
    "interaction.honey_guard.completed"
)
INTERACTION_EVENT_FOOD_SHARE_COMPLETED = (
    "interaction.food_share.completed"
)
AMBIENT_EVENT_TSUYOSHI_SIDE_READY_FOLLOWUP = (
    "ambient.tsuyoshi.side_ready_followup"
)

KNOWN_ACTIVITY_EVENT_NAMES = frozenset(
    {
        ACTIVITY_EVENT_WORK_COMPLETED,
        ACTIVITY_EVENT_RACE_COMPLETED,
        ACTIVITY_EVENT_RACE_DECLINED,
        ACTIVITY_EVENT_CHORUS_COMPLETED,
        ACTIVITY_EVENT_CHORUS_INTERRUPTED,
        ACTIVITY_EVENT_SLEEP_STARTED,
        ACTIVITY_EVENT_SLEEP_COMPLETED,
        ACTIVITY_EVENT_SLEEP_INTERRUPTED,
        ACTIVITY_EVENT_SLEEP_GROUP_JOINED,
        ACTIVITY_EVENT_TRANSFORMATION_COMPLETED,
        INTERACTION_EVENT_CARE_COMPLETED,
        INTERACTION_EVENT_HONEY_GUARD_COMPLETED,
        INTERACTION_EVENT_FOOD_SHARE_COMPLETED,
        AMBIENT_EVENT_TSUYOSHI_SIDE_READY_FOLLOWUP,
    }
)


def normalize_activity_participants(participants) -> list[dict[str, str]]:
    if isinstance(participants, Mapping):
        items: Iterable[tuple[object, object]] = participants.items()
    else:
        items = tuple(participants or ())
    normalized = []
    for item in items:
        if isinstance(item, Mapping):
            name = item.get("name", "")
            role = item.get("role", "")
        else:
            try:
                name, role = item
            except (TypeError, ValueError):
                continue
        name = str(name or "").strip()
        role = str(role or "").strip()
        if name:
            normalized.append({"name": name, "role": role})
    return normalized


def build_activity_event_metadata(
    *,
    event_name: str,
    activity_id: str,
    activity_kind: str,
    participants=(),
    source: str = "",
    execution_mode: str = "",
    world_mode: str = "",
    phase: str = "",
    started_at: float = 0.0,
    ended_at: float = 0.0,
    outcome: str = "",
    reason: str = "",
    event_id: str = "",
    extra: Mapping[str, object] | None = None,
) -> dict[str, object]:
    event_name = str(event_name or "").strip()
    if event_name not in KNOWN_ACTIVITY_EVENT_NAMES:
        raise ValueError(f"unknown activity event name: {event_name}")
    started_at = float(started_at or 0.0)
    ended_at = float(ended_at or 0.0)
    payload = {
        "activity_event_schema_version": (
            ACTIVITY_EVENT_PAYLOAD_SCHEMA_VERSION
        ),
        "activity_event_name": event_name,
        "activity_event_id": str(event_id or ""),
        "activity_id": str(activity_id or ""),
        "activity_kind": str(activity_kind or ""),
        "activity_phase": str(phase or ""),
        "activity_source": str(source or ""),
        "activity_execution_mode": str(execution_mode or ""),
        "activity_world_mode": str(world_mode or ""),
        "activity_started_at": started_at,
        "activity_ended_at": ended_at,
        "activity_elapsed_seconds": max(0.0, ended_at - started_at),
        "activity_outcome": str(outcome or ""),
        "activity_reason": str(reason or ""),
        "activity_participants": normalize_activity_participants(
            participants
        ),
    }
    payload.update(dict(extra or {}))
    return payload
