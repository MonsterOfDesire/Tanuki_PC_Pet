from __future__ import annotations

from dataclasses import dataclass

from .activity_state import (
    ActivityPhaseSpec,
    ActivitySpec,
    COLLISION_POLICY_IGNORE,
    INTERRUPT_POLICY_ALLOW,
)
from .asset_selection_rules import get_mood_band
from .chorus_state import (
    CHORUS_REACTION_AUDIENCE,
    CHORUS_REACTION_PERFORM,
)
from .transformation_state import FORM_BASE, FORM_TRANSFORMED


CHORUS_ACTIVITY_KIND = "chorus"
CHORUS_APPROACH_PHASE = "approaching"
CHORUS_PERFORM_PHASE = "performing"
CHORUS_OBSERVE_PHASE = "observing"
CHORUS_FINISH_PHASE = "finishing"

CHORUS_BASE_DURATION_SECONDS = 60.0
CHORUS_EXTRA_PERFORMER_SECONDS = 30.0
CHORUS_MAX_DURATION_SECONDS = 180.0
CHORUS_LATE_JOIN_MIN_REMAINING_SECONDS = 30.0
CHORUS_FINISH_SECONDS = 2.5
CHORUS_APPROACH_TIMEOUT_SECONDS = 60.0
CHORUS_PHASE_SENTINEL_SECONDS = 24.0 * 60.0 * 60.0
CHORUS_NOTICE_MAX_DISTANCE = 1500.0
CHORUS_RECONSIDER_INTERVAL_SECONDS = 1.0
CHORUS_ARRIVAL_DISTANCE = 10.0
CHORUS_APPROACH_SPEED_SCALE = 1.0
CHORUS_APPROACH_MIN_SPEED = 3.0
CHORUS_SLOT_GAP = 24.0
CHORUS_AUDIENCE_SLOT_BASE = 3

CHORUS_INITIAL_DELAY_MIN_SECONDS = 120.0
CHORUS_INITIAL_DELAY_MAX_SECONDS = 240.0
CHORUS_RETRY_MIN_SECONDS = 30.0
CHORUS_RETRY_MAX_SECONDS = 60.0
CHORUS_COOLDOWN_MIN_SECONDS = 180.0
CHORUS_COOLDOWN_MAX_SECONDS = 360.0

CHORUS_FREQUENCY_MULTIPLIERS = {
    "frequent": 0.5,
    "normal": 1.0,
    "occasional": 2.0,
}

CHORUS_BLOCKED_OPERATIONS = frozenset(
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

CHORUS_AUTONOMOUS_FORMS = frozenset(
    {
        ("Tsurumaru Tsuyoshi", FORM_BASE),
        ("Sirius Symboli", FORM_BASE),
        ("Tokai Teio", FORM_BASE),
        ("Tokai Teio", FORM_TRANSFORMED),
        ("Symboli Rudolf", FORM_TRANSFORMED),
    }
)


@dataclass(frozen=True)
class ChorusEligibilitySnapshot:
    character_name: str
    form_key: str
    world_mode: str
    mood_score: float
    visible: bool = True
    enabled: bool = True
    grounded: bool = True
    busy: bool = False
    capability_ready: bool = True


@dataclass(frozen=True)
class ChorusEligibilityDecision:
    allowed: bool
    reason: str = ""
    mood_band: str = ""


@dataclass(frozen=True)
class ChorusReactionDecision:
    reaction: str
    perform_probability: float
    audience_probability: float


@dataclass(frozen=True)
class ChorusSchedulePolicy:
    initial_delay_min_seconds: float
    initial_delay_max_seconds: float
    retry_min_seconds: float
    retry_max_seconds: float
    cooldown_min_seconds: float
    cooldown_max_seconds: float


def get_chorus_schedule_policy(
    frequency_key: str = "normal",
) -> ChorusSchedulePolicy:
    multiplier = CHORUS_FREQUENCY_MULTIPLIERS.get(
        str(frequency_key or "normal"),
        CHORUS_FREQUENCY_MULTIPLIERS["normal"],
    )
    return ChorusSchedulePolicy(
        initial_delay_min_seconds=CHORUS_INITIAL_DELAY_MIN_SECONDS * multiplier,
        initial_delay_max_seconds=CHORUS_INITIAL_DELAY_MAX_SECONDS * multiplier,
        retry_min_seconds=CHORUS_RETRY_MIN_SECONDS * multiplier,
        retry_max_seconds=CHORUS_RETRY_MAX_SECONDS * multiplier,
        cooldown_min_seconds=CHORUS_COOLDOWN_MIN_SECONDS * multiplier,
        cooldown_max_seconds=CHORUS_COOLDOWN_MAX_SECONDS * multiplier,
    )


def evaluate_chorus_eligibility(
    snapshot: ChorusEligibilitySnapshot,
    *,
    autonomous_start: bool = False,
) -> ChorusEligibilityDecision:
    mood_band = get_mood_band(float(snapshot.mood_score))
    if str(snapshot.world_mode or "") not in {"sandbox", "golden_legend"}:
        return ChorusEligibilityDecision(False, "world_mode_disabled", mood_band)
    if not str(snapshot.character_name or "").strip():
        return ChorusEligibilityDecision(False, "missing_character_name", mood_band)
    if autonomous_start and (
        str(snapshot.character_name), str(snapshot.form_key or FORM_BASE)
    ) not in CHORUS_AUTONOMOUS_FORMS:
        return ChorusEligibilityDecision(False, "form_cannot_initiate", mood_band)
    if not snapshot.enabled:
        return ChorusEligibilityDecision(False, "participant_disabled", mood_band)
    if not snapshot.visible:
        return ChorusEligibilityDecision(False, "participant_hidden", mood_band)
    if mood_band == "severe":
        return ChorusEligibilityDecision(False, "severe_mood", mood_band)
    if not snapshot.grounded:
        return ChorusEligibilityDecision(False, "participant_airborne", mood_band)
    if snapshot.busy:
        return ChorusEligibilityDecision(False, "participant_busy", mood_band)
    if not snapshot.capability_ready:
        return ChorusEligibilityDecision(False, "animation_unavailable", mood_band)
    return ChorusEligibilityDecision(True, mood_band=mood_band)


def decide_chorus_reaction(
    *,
    mood_score: float,
    roll: float,
    can_perform: bool,
    can_observe: bool,
) -> ChorusReactionDecision:
    mood_band = get_mood_band(float(mood_score))
    if mood_band == "severe":
        return ChorusReactionDecision("ignore", 0.0, 0.0)
    if mood_band == "normal":
        perform_weight, audience_weight, ignore_weight = 0.45, 0.35, 0.20
    else:
        perform_weight, audience_weight, ignore_weight = 0.20, 0.35, 0.45
    if not can_perform:
        perform_weight = 0.0
    if not can_observe:
        audience_weight = 0.0
    total = perform_weight + audience_weight + ignore_weight
    if total <= 0.0:
        return ChorusReactionDecision("ignore", 0.0, 0.0)
    perform_probability = perform_weight / total
    audience_probability = audience_weight / total
    normalized_roll = max(0.0, min(0.999999, float(roll)))
    if normalized_roll < perform_probability:
        reaction = CHORUS_REACTION_PERFORM
    elif normalized_roll < perform_probability + audience_probability:
        reaction = CHORUS_REACTION_AUDIENCE
    else:
        reaction = "ignore"
    return ChorusReactionDecision(
        reaction,
        perform_probability,
        audience_probability,
    )


def extend_chorus_end_time(
    *,
    started_at: float,
    current_ends_at: float,
    now: float,
    performer_count: int,
) -> float:
    natural_end = float(started_at) + min(
        CHORUS_MAX_DURATION_SECONDS,
        CHORUS_BASE_DURATION_SECONDS
        + max(0, int(performer_count) - 1) * CHORUS_EXTRA_PERFORMER_SECONDS,
    )
    late_join_end = float(now) + CHORUS_LATE_JOIN_MIN_REMAINING_SECONDS
    hard_end = float(started_at) + CHORUS_MAX_DURATION_SECONDS
    return min(
        hard_end,
        max(float(current_ends_at), natural_end, late_join_end),
    )


def reserve_chorus_approach_time(
    *,
    started_at: float,
    current_ends_at: float,
    now: float,
) -> float:
    return min(
        float(started_at) + CHORUS_MAX_DURATION_SECONDS,
        max(
            float(current_ends_at),
            float(now)
            + CHORUS_APPROACH_TIMEOUT_SECONDS
            + CHORUS_LATE_JOIN_MIN_REMAINING_SECONDS,
        ),
    )


def build_chorus_activity_spec(
    reaction: str,
    *,
    begins_with_approach: bool,
) -> ActivitySpec:
    reaction = str(reaction or "")
    target_phase = (
        CHORUS_PERFORM_PHASE
        if reaction == CHORUS_REACTION_PERFORM
        else CHORUS_OBSERVE_PHASE
    )
    phases = []
    if begins_with_approach:
        phases.append(
            ActivityPhaseSpec(
                CHORUS_APPROACH_PHASE,
                CHORUS_APPROACH_TIMEOUT_SECONDS,
            )
        )
    phases.extend(
        (
            ActivityPhaseSpec(target_phase, CHORUS_PHASE_SENTINEL_SECONDS),
            ActivityPhaseSpec(CHORUS_FINISH_PHASE, CHORUS_FINISH_SECONDS),
        )
    )
    return ActivitySpec(
        kind=CHORUS_ACTIVITY_KIND,
        phases=tuple(phases),
        blocked_operations=CHORUS_BLOCKED_OPERATIONS,
        collision_policy=COLLISION_POLICY_IGNORE,
        interrupt_policy=INTERRUPT_POLICY_ALLOW,
    )
