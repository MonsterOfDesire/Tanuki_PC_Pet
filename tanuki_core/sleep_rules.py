from __future__ import annotations

from dataclasses import dataclass

from .activity_state import (
    ActivityPhaseSpec,
    ActivitySpec,
    COLLISION_POLICY_IGNORE,
    INTERRUPT_POLICY_ALLOW,
)


SLEEP_ACTIVITY_KIND = "sleep"
SLEEP_PROFILE_KEY = "sleep_v1"
SLEEP_ROLE = "sleeper"

SLEEP_SETTLING_PHASE = "settling"
SLEEPING_PHASE = "sleeping"
SLEEP_WAKING_PHASE = "waking"

SLEEP_SETTLING_SECONDS = 3.0
SLEEP_WAKING_SECONDS = 3.0
SLEEP_DURATION_MIN_SECONDS = 45.0
SLEEP_DURATION_MAX_SECONDS = 150.0
SLEEP_NATURAL_COMPLETION_MOOD_REWARD = 3.0
SLEEP_NATURAL_COMPLETION_MOOD_CEILING = 55.0

SLEEP_INITIAL_DELAY_MIN_SECONDS = 120.0
SLEEP_INITIAL_DELAY_MAX_SECONDS = 240.0
SLEEP_COOLDOWN_MIN_SECONDS = 180.0
SLEEP_COOLDOWN_MAX_SECONDS = 480.0
SLEEP_RETRY_MIN_SECONDS = 30.0
SLEEP_RETRY_MAX_SECONDS = 60.0
SLEEP_INTERRUPTED_COOLDOWN_MIN_SECONDS = 90.0
SLEEP_INTERRUPTED_COOLDOWN_MAX_SECONDS = 180.0
# 0 means runtime capacity follows the number of currently visible pets.
SLEEP_MAX_CONCURRENT = 0

SLEEP_TRIGGER_AUTONOMOUS = "autonomous"
SLEEP_TRIGGER_OBSERVED_JOIN = "observed_join"
SLEEP_TRIGGER_SANDBOX_CONTROL = "sandbox_control"
SLEEP_OBSERVE_MIN_SECONDS = 3.0
SLEEP_OBSERVE_MAX_SECONDS = 6.0
SLEEP_SOCIAL_PROBE_MIN_SECONDS = 30.0
SLEEP_SOCIAL_PROBE_MAX_SECONDS = 60.0
SLEEP_SOCIAL_RETRY_MIN_SECONDS = 60.0
SLEEP_SOCIAL_RETRY_MAX_SECONDS = 120.0
SLEEP_JOIN_MAX_DISTANCE = 520.0
SLEEP_JOIN_MOVE_SPEED_SCALE = 1.15
SLEEP_JOIN_ARRIVAL_DISTANCE = 8.0

SLEEP_BLOCKED_OPERATIONS = frozenset(
    {
        "random",
        "offer",
        "social_start",
        "observe_start",
        "care_give",
        "care_receive",
        "windowing",
    }
)


@dataclass
class SleepScheduleState:
    next_proposal_at: float = 0.0
    last_woke_at: float = 0.0
    awake_since: float = -1.0
    next_social_probe_at: float = 0.0


@dataclass(frozen=True)
class SleepEligibilitySnapshot:
    participant_name: str
    now: float
    next_proposal_at: float
    active_sleep_count: int = 0
    max_concurrent_sleepers: int = SLEEP_MAX_CONCURRENT


@dataclass(frozen=True)
class SleepEligibilityDecision:
    allowed: bool
    reason: str = ""


@dataclass(frozen=True)
class SleepJoinCandidateSnapshot:
    observer_name: str
    target_name: str
    distance: float
    target_is_sleeping: bool
    observer_busy: bool = False
    group_size: int = 1
    reserved_joiners: int = 0
    active_sleep_count: int = 0
    max_concurrent_sleepers: int = SLEEP_MAX_CONCURRENT


@dataclass(frozen=True)
class SleepJoinCandidateDecision:
    allowed: bool
    reason: str = ""


@dataclass(frozen=True)
class SleepJoinInfluenceSnapshot:
    awake_seconds: float
    autonomous_schedule_due: bool
    distance: float
    familiarity: float = 0.0
    attachment: float = 0.0
    tension: float = 0.0
    group_size: int = 1


@dataclass(frozen=True)
class SleepJoinInfluenceDecision:
    should_join: bool
    probability: float


def evaluate_sleep_eligibility(
    snapshot: SleepEligibilitySnapshot,
) -> SleepEligibilityDecision:
    if not str(snapshot.participant_name or "").strip():
        return SleepEligibilityDecision(False, "missing_participant_name")
    if float(snapshot.now) < float(snapshot.next_proposal_at):
        return SleepEligibilityDecision(False, "schedule_not_due")
    if (
        int(snapshot.max_concurrent_sleepers) > 0
        and int(snapshot.active_sleep_count)
        >= int(snapshot.max_concurrent_sleepers)
    ):
        return SleepEligibilityDecision(False, "sleep_capacity_reached")
    return SleepEligibilityDecision(True)


def evaluate_sleep_join_candidate(
    snapshot: SleepJoinCandidateSnapshot,
) -> SleepJoinCandidateDecision:
    if not str(snapshot.observer_name or "").strip():
        return SleepJoinCandidateDecision(False, "missing_observer_name")
    if not str(snapshot.target_name or "").strip():
        return SleepJoinCandidateDecision(False, "missing_target_name")
    if snapshot.observer_name == snapshot.target_name:
        return SleepJoinCandidateDecision(False, "same_participant")
    if snapshot.observer_busy:
        return SleepJoinCandidateDecision(False, "observer_busy")
    if not snapshot.target_is_sleeping:
        return SleepJoinCandidateDecision(False, "target_not_sleeping")
    if float(snapshot.distance) > SLEEP_JOIN_MAX_DISTANCE:
        return SleepJoinCandidateDecision(False, "target_too_far")
    if (
        int(snapshot.max_concurrent_sleepers) > 0
        and int(snapshot.active_sleep_count)
        >= int(snapshot.max_concurrent_sleepers)
    ):
        return SleepJoinCandidateDecision(False, "sleep_capacity_reached")
    return SleepJoinCandidateDecision(True)


def evaluate_sleep_join_influence(
    snapshot: SleepJoinInfluenceSnapshot,
    *,
    roll: float,
) -> SleepJoinInfluenceDecision:
    awake_factor = min(0.25, max(0.0, snapshot.awake_seconds) / 600.0)
    relation_factor = min(
        0.20,
        max(0.0, snapshot.familiarity) / 500.0
        + max(0.0, snapshot.attachment) / 400.0,
    )
    proximity_factor = max(
        0.0,
        1.0 - (max(0.0, snapshot.distance) / SLEEP_JOIN_MAX_DISTANCE),
    ) * 0.10
    tension_penalty = min(0.12, max(0.0, snapshot.tension) / 250.0)
    group_penalty = max(0, int(snapshot.group_size) - 1) * 0.08
    schedule_factor = 0.15 if snapshot.autonomous_schedule_due else 0.0
    probability = min(
        0.80,
        max(
            0.10,
            0.25
            + awake_factor
            + relation_factor
            + proximity_factor
            + schedule_factor
            - tension_penalty
            - group_penalty,
        ),
    )
    return SleepJoinInfluenceDecision(
        should_join=float(roll) < probability,
        probability=probability,
    )


def build_sleep_activity_spec(
    sleeping_seconds: float,
) -> ActivitySpec:
    sleeping_seconds = float(sleeping_seconds)
    if sleeping_seconds <= 0.0:
        raise ValueError("sleep duration must be positive")
    return ActivitySpec(
        kind=SLEEP_ACTIVITY_KIND,
        phases=(
            ActivityPhaseSpec(
                SLEEP_SETTLING_PHASE,
                SLEEP_SETTLING_SECONDS,
            ),
            ActivityPhaseSpec(
                SLEEPING_PHASE,
                sleeping_seconds,
            ),
            ActivityPhaseSpec(
                SLEEP_WAKING_PHASE,
                SLEEP_WAKING_SECONDS,
            ),
        ),
        blocked_operations=SLEEP_BLOCKED_OPERATIONS,
        collision_policy=COLLISION_POLICY_IGNORE,
        interrupt_policy=INTERRUPT_POLICY_ALLOW,
    )
