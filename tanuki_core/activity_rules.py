from __future__ import annotations

from dataclasses import dataclass

from .activity_state import (
    ActiveActivity,
    ActivityParticipantSnapshot,
    ActivitySpec,
    INTERRUPT_POLICY_ALLOW,
    ResolvedActivityPolicy,
)


@dataclass(frozen=True)
class ActivityStartDecision:
    allowed: bool
    reason: str = ""
    participant_name: str = ""


@dataclass(frozen=True)
class ActivityBusyDecision:
    busy: bool
    reason: str = ""
    activity_id: str = ""


@dataclass(frozen=True)
class ActivityInterruptDecision:
    allowed: bool
    reason: str = ""


def resolve_activity_policy(
    spec: ActivitySpec,
    phase_index: int,
) -> ResolvedActivityPolicy:
    phase = spec.phases[phase_index]
    return ResolvedActivityPolicy(
        blocked_operations=(
            spec.blocked_operations
            if phase.blocked_operations is None
            else phase.blocked_operations
        ),
        collision_policy=phase.collision_policy or spec.collision_policy,
        interrupt_policy=phase.interrupt_policy or spec.interrupt_policy,
    )


def evaluate_activity_start(
    spec: ActivitySpec,
    owner_name: str,
    participant_snapshots: tuple[ActivityParticipantSnapshot, ...],
) -> ActivityStartDecision:
    _ = spec
    owner_name = str(owner_name or "").strip()
    snapshots = tuple(participant_snapshots or ())
    if not snapshots:
        return ActivityStartDecision(False, "no_participants")

    participant_names = tuple(
        snapshot.participant.name
        for snapshot in snapshots
    )
    if len(set(participant_names)) != len(participant_names):
        return ActivityStartDecision(False, "duplicate_participant")
    if owner_name not in participant_names:
        return ActivityStartDecision(False, "owner_not_participant", owner_name)

    for snapshot in snapshots:
        participant_name = snapshot.participant.name
        if not snapshot.enabled:
            return ActivityStartDecision(
                False,
                "participant_disabled",
                participant_name,
            )
        if not snapshot.visible:
            return ActivityStartDecision(
                False,
                "participant_hidden",
                participant_name,
            )
        if snapshot.active_activity_id:
            return ActivityStartDecision(
                False,
                "participant_owned",
                participant_name,
            )
        if snapshot.busy_reasons:
            return ActivityStartDecision(
                False,
                f"participant_busy:{snapshot.busy_reasons[0]}",
                participant_name,
            )
        if not snapshot.capability_ready:
            reason = snapshot.capability_reason or "unavailable"
            return ActivityStartDecision(
                False,
                f"capability_unavailable:{reason}",
                participant_name,
            )

    return ActivityStartDecision(True)


def decide_activity_busy(
    activity: ActiveActivity,
    operation: str,
) -> ActivityBusyDecision:
    operation = str(operation or "").strip()
    if operation == "activity_start":
        return ActivityBusyDecision(
            True,
            reason=(
                f"activity:{activity.spec.kind}:"
                f"{activity.phase.name}:owns_participant"
            ),
            activity_id=activity.activity_id,
        )
    policy = resolve_activity_policy(activity.spec, activity.phase_index)
    if operation and operation in policy.blocked_operations:
        return ActivityBusyDecision(
            True,
            reason=f"activity:{activity.spec.kind}:{activity.phase.name}",
            activity_id=activity.activity_id,
        )
    return ActivityBusyDecision(False)


def decide_activity_interrupt(
    activity: ActiveActivity,
    *,
    force: bool,
) -> ActivityInterruptDecision:
    if force:
        return ActivityInterruptDecision(True)
    policy = resolve_activity_policy(activity.spec, activity.phase_index)
    if policy.interrupt_policy == INTERRUPT_POLICY_ALLOW:
        return ActivityInterruptDecision(True)
    return ActivityInterruptDecision(False, "interrupt_requires_force")
