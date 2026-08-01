from __future__ import annotations

from dataclasses import dataclass

SLEEP_JOIN_PHASE_OBSERVING = "observing"
SLEEP_JOIN_PHASE_APPROACHING = "approaching"


@dataclass
class SleepJoinAttemptState:
    observer_name: str
    target_name: str
    target_activity_id: str
    phase: str
    phase_ends_at: float
    started_at: float
    group_id: str = ""
    anchor_name: str = ""
    slot: int = 0
    animation_applied: bool = False


@dataclass(frozen=True)
class SleepGroupJoinPlan:
    allowed: bool
    reason: str = ""
    group_id: str = ""
    anchor_name: str = ""
    slot: int = 0


def choose_sleep_group_slot(occupied_slots) -> int:
    occupied = {int(slot) for slot in occupied_slots or ()}
    distance = 1
    while True:
        for slot in (distance, -distance):
            if slot not in occupied:
                return slot
        distance += 1


def build_sleep_group_join_plan(
    *,
    target_activity_id: str,
    target_name: str,
    existing_group_id: str = "",
    existing_anchor_name: str = "",
    occupied_slots=(),
) -> SleepGroupJoinPlan:
    target_activity_id = str(target_activity_id or "").strip()
    target_name = str(target_name or "").strip()
    if not target_activity_id or not target_name:
        return SleepGroupJoinPlan(False, "missing_sleep_target")
    slot = choose_sleep_group_slot(occupied_slots)
    return SleepGroupJoinPlan(
        True,
        group_id=(
            str(existing_group_id or "").strip()
            or f"sleep-group:{target_activity_id}"
        ),
        anchor_name=(
            str(existing_anchor_name or "").strip() or target_name
        ),
        slot=slot,
    )


def resolve_sleep_join_target_x(
    *,
    anchor_x: float,
    anchor_width: float,
    joiner_width: float,
    slot: int,
) -> float:
    normalized_slot = int(slot) or 1
    direction = 1 if normalized_slot >= 0 else -1
    center_spacing = max(
        48.0,
        (max(1.0, float(anchor_width)) + max(1.0, float(joiner_width)))
        * 0.35,
    )
    anchor_center = float(anchor_x) + (float(anchor_width) / 2.0)
    joiner_center = anchor_center + (
        direction * center_spacing * abs(normalized_slot)
    )
    return joiner_center - (float(joiner_width) / 2.0)
