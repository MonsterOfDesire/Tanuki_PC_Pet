from __future__ import annotations

from dataclasses import dataclass

from .activity_state import (
    ActivityPhaseSpec,
    ActivitySpec,
    COLLISION_POLICY_IGNORE,
    INTERRUPT_POLICY_ALLOW,
)
from .asset_selection_rules import get_mood_band
from .race_state import RaceLaneGeometry, RacePerformanceDecision


RACE_ACTIVITY_KIND = "race"
RACE_PROFILE_KEY = "race_v1"
RACE_CHALLENGER_ROLE = "challenger"
RACE_OPPONENT_ROLE = "opponent"

RACE_CHALLENGE_PHASE = "challenge"
RACE_RESPONSE_PHASE = "response"
RACE_TO_START_PHASE = "to_start"
RACE_READY_PHASE = "ready"
RACE_RUNNING_PHASE = "running"
RACE_FINISH_PHASE = "finish"
RACE_RECOVERY_PHASE = "recovery"

RACE_CHALLENGE_SECONDS = 2.0
RACE_RESPONSE_SECONDS = 2.0
RACE_TO_START_TIMEOUT_SECONDS = 24.0
RACE_READY_SECONDS = 2.0
RACE_RUNNING_TIMEOUT_SECONDS = 36.0
RACE_FINISH_SECONDS = 3.0
RACE_RECOVERY_SECONDS = 4.0

RACE_INITIAL_DELAY_MIN_SECONDS = 180.0
RACE_INITIAL_DELAY_MAX_SECONDS = 300.0
RACE_RETRY_MIN_SECONDS = 60.0
RACE_RETRY_MAX_SECONDS = 120.0
RACE_COOLDOWN_MIN_SECONDS = 300.0
RACE_COOLDOWN_MAX_SECONDS = 480.0

RACE_START_GAP = 84.0
RACE_START_GAP_MAX = 160.0
RACE_START_GAP_WIDTH_SCALE = 0.25
RACE_LANE_PADDING = 48.0
RACE_MIN_DISTANCE = 420.0
RACE_MAX_DISTANCE = 1100.0
RACE_ARRIVAL_DISTANCE = 6.0
RACE_TO_START_SPEED_SCALE = 1.35
RACE_RUNNING_SPEED_SCALE = 1.0
RACE_FINISH_MAX_SEPARATION = 150.0
RACE_FINISH_STANDOFF_DISTANCE = 120.0
RACE_CHALLENGE_MAX_DISTANCE = 420.0
RACE_SPEED_VARIATION = 0.15
RACE_SPEED_MOOD_REFERENCE = 50.0
RACE_SPEED_MOOD_MIN = 20.0
RACE_SPEED_MOOD_MAX = 100.0
RACE_POST_INTERACTION_SECONDS = 1.6
RACE_CHALLENGE_SPACING_PADDING = 24.0
RACE_TO_START_STALL_REPLAN_SECONDS = 2.0

RACE_SANDBOX_INITIAL_DELAY_MIN_SECONDS = 120.0
RACE_SANDBOX_INITIAL_DELAY_MAX_SECONDS = 240.0
RACE_SANDBOX_RETRY_MIN_SECONDS = 30.0
RACE_SANDBOX_RETRY_MAX_SECONDS = 60.0
RACE_SANDBOX_COOLDOWN_MIN_SECONDS = 180.0
RACE_SANDBOX_COOLDOWN_MAX_SECONDS = 300.0

RACE_ADULT_NAMES = frozenset(
    {
        "Symboli Rudolf",
        "Sirius Symboli",
    }
)

RACE_SPEED_PROFILES = {
    ("Symboli Rudolf", "transformed"): (8.4, 0.005),
    ("Sirius Symboli", "base"): (6.05, 0.015),
    ("Tokai Teio", "base"): (5.5, 0.025),
    ("Symboli Rudolf", "base"): (5.575, 0.010),
}

RACE_BLOCKED_OPERATIONS = frozenset(
    {
        "random",
        "offer",
        "social_start",
        "observe_start",
        "care_give",
        "care_receive",
        "windowing",
        "drag",
    }
)


@dataclass(frozen=True)
class RaceEligibilitySnapshot:
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
class RaceEligibilityDecision:
    allowed: bool
    reason: str = ""
    mood_band: str = ""


@dataclass(frozen=True)
class RaceAcceptanceDecision:
    accepted: bool
    probability: float


@dataclass(frozen=True)
class RaceEmergencySnapshot:
    distressed_child_names: tuple[str, ...] = ()
    tsuyoshi_has_honey: bool = False


@dataclass(frozen=True)
class RaceEmergencyDecision:
    should_interrupt: bool
    reason: str = ""


@dataclass(frozen=True)
class RaceSchedulePolicy:
    initial_min_seconds: float
    initial_max_seconds: float
    retry_min_seconds: float
    retry_max_seconds: float
    cooldown_min_seconds: float
    cooldown_max_seconds: float


RACE_SCHEDULE_POLICIES = {
    "golden_legend": RaceSchedulePolicy(
        RACE_INITIAL_DELAY_MIN_SECONDS,
        RACE_INITIAL_DELAY_MAX_SECONDS,
        RACE_RETRY_MIN_SECONDS,
        RACE_RETRY_MAX_SECONDS,
        RACE_COOLDOWN_MIN_SECONDS,
        RACE_COOLDOWN_MAX_SECONDS,
    ),
    "sandbox": RaceSchedulePolicy(
        RACE_SANDBOX_INITIAL_DELAY_MIN_SECONDS,
        RACE_SANDBOX_INITIAL_DELAY_MAX_SECONDS,
        RACE_SANDBOX_RETRY_MIN_SECONDS,
        RACE_SANDBOX_RETRY_MAX_SECONDS,
        RACE_SANDBOX_COOLDOWN_MIN_SECONDS,
        RACE_SANDBOX_COOLDOWN_MAX_SECONDS,
    ),
}
RACE_FREQUENCY_MULTIPLIERS = {
    "frequent": 0.5,
    "normal": 1.0,
    "occasional": 2.0,
}


def get_race_schedule_policy(
    world_mode: str,
    frequency_key: str = "normal",
) -> RaceSchedulePolicy | None:
    base = RACE_SCHEDULE_POLICIES.get(str(world_mode or ""))
    if base is None:
        return None
    multiplier = RACE_FREQUENCY_MULTIPLIERS.get(
        str(frequency_key or "normal"),
        1.0,
    )
    return RaceSchedulePolicy(
        initial_min_seconds=base.initial_min_seconds * multiplier,
        initial_max_seconds=base.initial_max_seconds * multiplier,
        retry_min_seconds=base.retry_min_seconds * multiplier,
        retry_max_seconds=base.retry_max_seconds * multiplier,
        cooldown_min_seconds=base.cooldown_min_seconds * multiplier,
        cooldown_max_seconds=base.cooldown_max_seconds * multiplier,
    )


def build_race_activity_spec() -> ActivitySpec:
    return ActivitySpec(
        kind=RACE_ACTIVITY_KIND,
        phases=(
            ActivityPhaseSpec(RACE_CHALLENGE_PHASE, RACE_CHALLENGE_SECONDS),
            ActivityPhaseSpec(RACE_RESPONSE_PHASE, RACE_RESPONSE_SECONDS),
            ActivityPhaseSpec(
                RACE_TO_START_PHASE,
                RACE_TO_START_TIMEOUT_SECONDS,
            ),
            ActivityPhaseSpec(RACE_READY_PHASE, RACE_READY_SECONDS),
            ActivityPhaseSpec(
                RACE_RUNNING_PHASE,
                RACE_RUNNING_TIMEOUT_SECONDS,
            ),
            ActivityPhaseSpec(RACE_FINISH_PHASE, RACE_FINISH_SECONDS),
            ActivityPhaseSpec(RACE_RECOVERY_PHASE, RACE_RECOVERY_SECONDS),
        ),
        blocked_operations=RACE_BLOCKED_OPERATIONS,
        collision_policy=COLLISION_POLICY_IGNORE,
        interrupt_policy=INTERRUPT_POLICY_ALLOW,
    )


def evaluate_race_eligibility(
    snapshot: RaceEligibilitySnapshot,
    *,
    preview: bool = False,
) -> RaceEligibilityDecision:
    mood_band = get_mood_band(float(snapshot.mood_score))
    world_mode = str(snapshot.world_mode or "")
    if (preview and world_mode != "sandbox") or (
        not preview and world_mode not in RACE_SCHEDULE_POLICIES
    ):
        return RaceEligibilityDecision(
            False,
            "preview_requires_sandbox" if preview else "world_mode_disabled",
            mood_band,
        )
    if not snapshot.enabled:
        return RaceEligibilityDecision(False, "participant_disabled", mood_band)
    if not snapshot.visible:
        return RaceEligibilityDecision(False, "participant_hidden", mood_band)
    if not snapshot.capability_ready:
        return RaceEligibilityDecision(False, "form_blocks_race", mood_band)
    if mood_band == "severe":
        return RaceEligibilityDecision(False, "severe_mood", mood_band)
    if not snapshot.grounded:
        return RaceEligibilityDecision(False, "participant_airborne", mood_band)
    if snapshot.busy:
        return RaceEligibilityDecision(False, "participant_busy", mood_band)
    return RaceEligibilityDecision(True, mood_band=mood_band)


def decide_race_acceptance(
    *,
    opponent_name: str,
    opponent_form: str,
    mood_score: float,
    roll: float,
) -> RaceAcceptanceDecision:
    mood_band = get_mood_band(float(mood_score))
    if str(opponent_name or "") == "Tokai Teio" and mood_band == "normal":
        probability = 1.0
    elif str(opponent_form or "") == "transformed":
        probability = 0.95
    elif mood_band == "normal":
        probability = 0.85
    else:
        probability = 0.60
    return RaceAcceptanceDecision(float(roll) < probability, probability)


def evaluate_race_emergency_interrupt(
    snapshot: RaceEmergencySnapshot,
) -> RaceEmergencyDecision:
    if snapshot.tsuyoshi_has_honey:
        return RaceEmergencyDecision(True, "tsuyoshi_honey_guard_needed")
    if tuple(snapshot.distressed_child_names or ()):
        return RaceEmergencyDecision(True, "child_care_needed")
    return RaceEmergencyDecision(False)


def race_pair_is_close(distance: float) -> bool:
    return 0.0 <= float(distance) <= RACE_CHALLENGE_MAX_DISTANCE


def race_pair_has_valid_spacing(
    distance: float,
    *,
    participant_radii: tuple[float, float],
) -> bool:
    return not race_pair_spacing_reason(
        distance,
        participant_radii=participant_radii,
    )


def race_pair_spacing_reason(
    distance: float,
    *,
    participant_radii: tuple[float, float],
) -> str:
    minimum_distance = max(
        0.0,
        sum(max(0.0, float(radius)) for radius in participant_radii)
        + RACE_CHALLENGE_SPACING_PADDING,
    )
    distance = float(distance)
    if distance < minimum_distance:
        return "participants_too_close"
    if distance > RACE_CHALLENGE_MAX_DISTANCE:
        return "participants_too_far"
    return ""


def get_race_expected_speed(
    *,
    character_name: str,
    form_key: str,
    mood_score: float,
) -> float:
    name = str(character_name or "")
    form = str(form_key or "base")
    base_speed, mood_sensitivity = RACE_SPEED_PROFILES.get(
        (name, form),
        RACE_SPEED_PROFILES.get((name, "base"), (5.0, 0.01)),
    )
    bounded_mood = max(
        RACE_SPEED_MOOD_MIN,
        min(RACE_SPEED_MOOD_MAX, float(mood_score)),
    )
    mood_adjustment = (
        bounded_mood - RACE_SPEED_MOOD_REFERENCE
    ) * mood_sensitivity
    return max(1.0, float(base_speed) + mood_adjustment)


def sample_race_speed(base_speed: float, *, roll: float) -> float:
    normalized_roll = max(0.0, min(1.0, float(roll)))
    variation = (normalized_roll - 0.5) * 2.0 * RACE_SPEED_VARIATION
    return max(1.0, float(base_speed) + variation)


def decide_race_performance(
    *,
    challenger_name: str,
    challenger_form: str,
    challenger_mood_score: float,
    challenger_roll: float,
    opponent_name: str,
    opponent_form: str,
    opponent_mood_score: float,
    opponent_roll: float,
) -> RacePerformanceDecision:
    challenger_speed = sample_race_speed(
        get_race_expected_speed(
            character_name=challenger_name,
            form_key=challenger_form,
            mood_score=challenger_mood_score,
        ),
        roll=challenger_roll,
    )
    opponent_speed = sample_race_speed(
        get_race_expected_speed(
            character_name=opponent_name,
            form_key=opponent_form,
            mood_score=opponent_mood_score,
        ),
        roll=opponent_roll,
    )
    winner_name = (
        str(challenger_name)
        if challenger_speed >= opponent_speed
        else str(opponent_name)
    )
    return RacePerformanceDecision(
        winner_name=winner_name,
        challenger_speed=challenger_speed,
        opponent_speed=opponent_speed,
    )


def race_finish_is_ready(*, winner_arrived: bool, separation: float) -> bool:
    return bool(
        winner_arrived
        and float(separation) <= RACE_FINISH_MAX_SEPARATION
    )


def resolve_race_finish_band(
    *,
    character_name: str,
    opponent_name: str,
    winner: bool,
    transformed: bool = False,
) -> str:
    if bool(winner) or bool(transformed):
        return "normal"
    if (
        str(character_name or "") in RACE_ADULT_NAMES
        and str(opponent_name or "") == "Tokai Teio"
    ):
        return "normal"
    return "low"


def build_race_lane_geometry(
    *,
    left_bound: float,
    right_bound: float,
    participant_widths: tuple[float, float],
    participant_radii: tuple[float, float] | None = None,
    participant_positions: tuple[float, float] | None = None,
) -> RaceLaneGeometry:
    left = float(left_bound)
    right = float(right_bound)
    maximum_width = max(1.0, *(float(value) for value in participant_widths))
    safe_left = min(right, left + RACE_LANE_PADDING)
    safe_right = max(
        safe_left,
        right - maximum_width - RACE_LANE_PADDING,
    )
    if participant_radii is None:
        desired_gap = min(
            RACE_START_GAP_MAX,
            max(RACE_START_GAP, maximum_width * RACE_START_GAP_WIDTH_SCALE),
        )
    else:
        desired_gap = max(
            RACE_START_GAP,
            sum(max(0.0, float(radius)) for radius in participant_radii)
            + RACE_CHALLENGE_SPACING_PADDING,
        )
    usable_gap = min(desired_gap, max(0.0, safe_right - safe_left))
    half_gap = usable_gap / 2.0
    if participant_positions is None:
        course_center_x = safe_left + half_gap
    else:
        course_center_x = sum(
            float(value) for value in participant_positions
        ) / max(1, len(participant_positions))
    course_center_x = max(
        safe_left + half_gap,
        min(safe_right - half_gap, course_center_x),
    )
    left_distance = max(0.0, course_center_x - safe_left)
    right_distance = max(0.0, safe_right - course_center_x)
    direction = 1 if right_distance >= left_distance else -1
    available_distance = max(
        0.0,
        (right_distance if direction > 0 else left_distance) - half_gap,
    )
    if (
        available_distance < RACE_MIN_DISTANCE
        and safe_right - safe_left >= RACE_MIN_DISTANCE + usable_gap
    ):
        if direction > 0:
            course_center_x = max(
                safe_left + half_gap,
                safe_right - half_gap - RACE_MIN_DISTANCE,
            )
        else:
            course_center_x = min(
                safe_right - half_gap,
                safe_left + half_gap + RACE_MIN_DISTANCE,
            )
        left_distance = max(0.0, course_center_x - safe_left)
        right_distance = max(0.0, safe_right - course_center_x)
        available_distance = max(
            0.0,
            (right_distance if direction > 0 else left_distance) - half_gap,
        )
    distance = min(RACE_MAX_DISTANCE, available_distance)
    finish_x = course_center_x + (direction * distance)
    challenger_start_x = course_center_x - (direction * half_gap)
    opponent_start_x = course_center_x + (direction * half_gap)
    return RaceLaneGeometry(
        challenger_start_x=challenger_start_x,
        opponent_start_x=opponent_start_x,
        finish_x=finish_x,
        direction=direction,
        distance=distance,
    )
