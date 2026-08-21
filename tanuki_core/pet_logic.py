from dataclasses import dataclass


CLICK_RELEASE = "click"
LONG_HOLD_RELEASE = "long_hold"
DRAG_RELEASE = "drag_release"
TICK_PHASE_DRAGGING = "dragging"
TICK_PHASE_WINDOW_PERCH = "window_perch"
TICK_PHASE_WINDOW_FLIGHT = "window_flight"
TICK_PHASE_AIRBORNE = "airborne"
TICK_PHASE_RUN_AI = "run_ai"
AI_PHASE_ANGRY_LOCKED = "angry_locked"
AI_PHASE_RECOVERY_ACTIVE = "recovery_active"
AI_PHASE_RECOVERY_FINISHED = "recovery_finished"
AI_PHASE_NORMAL = "normal"
AI_FOLLOWUP_CARE_LOCK = "care_lock"
AI_FOLLOWUP_CARE = "care"
AI_FOLLOWUP_SOCIAL = "social"
AI_FOLLOWUP_RANDOM = "random"
NATURAL_MOOD_PAUSED_ACTIVITY_KINDS = frozenset({"sleep", "chorus"})


@dataclass(frozen=True)
class MoodUpdate:
    mood_score: float
    mood_state: str
    lonely_timer: int


@dataclass(frozen=True)
class MoodClimateProfile:
    change_chance: float
    negative_chance: float
    positive_delta_min: float
    positive_delta_max: float
    negative_delta_min: float
    negative_delta_max: float
    companion_relief: float
    companion_positive_bonus: float
    adult_comfort_relief: float
    adult_comfort_positive_bonus: float
    child_separation_chance_bonus: float
    child_separation_magnitude_bonus: float
    child_lonely_chance_bonus: float
    child_lonely_magnitude_scale: float
    child_low_recovery_bias: float
    adult_negative_magnitude_scale: float
    adult_low_recovery_bias: float
    adult_severe_recovery_bias: float


MOOD_CLIMATE_PROFILES = {
    # Climate controls how often natural mood changes occur, which direction
    # they favour, and their size. It deliberately has no target score: a low
    # mood must not be pulled upward merely because it crossed an invisible
    # equilibrium point.
    "cheerful": MoodClimateProfile(
        change_chance=0.50,
        negative_chance=0.10,
        positive_delta_min=0.20,
        positive_delta_max=0.60,
        negative_delta_min=0.05,
        negative_delta_max=0.18,
        companion_relief=0.03,
        companion_positive_bonus=0.10,
        adult_comfort_relief=0.06,
        adult_comfort_positive_bonus=0.30,
        child_separation_chance_bonus=0.06,
        child_separation_magnitude_bonus=0.08,
        child_lonely_chance_bonus=0.08,
        child_lonely_magnitude_scale=1.15,
        child_low_recovery_bias=0.00,
        adult_negative_magnitude_scale=1.00,
        adult_low_recovery_bias=0.00,
        adult_severe_recovery_bias=0.00,
    ),
    "balanced": MoodClimateProfile(
        change_chance=0.68,
        negative_chance=0.66,
        positive_delta_min=0.18,
        positive_delta_max=0.42,
        negative_delta_min=0.25,
        negative_delta_max=0.55,
        companion_relief=0.02,
        companion_positive_bonus=0.03,
        adult_comfort_relief=0.00,
        adult_comfort_positive_bonus=0.03,
        child_separation_chance_bonus=0.02,
        child_separation_magnitude_bonus=0.04,
        child_lonely_chance_bonus=0.01,
        child_lonely_magnitude_scale=1.02,
        child_low_recovery_bias=0.19,
        adult_negative_magnitude_scale=0.85,
        adult_low_recovery_bias=0.15,
        adult_severe_recovery_bias=0.08,
    ),
    "expressive": MoodClimateProfile(
        change_chance=0.90,
        negative_chance=0.68,
        positive_delta_min=0.15,
        positive_delta_max=0.45,
        negative_delta_min=0.45,
        negative_delta_max=1.05,
        companion_relief=0.10,
        companion_positive_bonus=0.10,
        adult_comfort_relief=0.28,
        adult_comfort_positive_bonus=0.30,
        child_separation_chance_bonus=0.20,
        child_separation_magnitude_bonus=0.55,
        child_lonely_chance_bonus=0.08,
        child_lonely_magnitude_scale=1.15,
        child_low_recovery_bias=0.00,
        adult_negative_magnitude_scale=0.45,
        adult_low_recovery_bias=0.25,
        adult_severe_recovery_bias=0.18,
    ),
}


MOOD_NEARBY_RADIUS_PX = 250.0
MOOD_ADULT_COMFORT_DISTANCE_PX = 300.0
MOOD_ADULT_FULL_SEPARATION_DISTANCE_PX = 1200.0


@dataclass(frozen=True)
class ReleaseDecision:
    kind: str
    next_click_count: int
    mood_delta: float
    starts_click_reset_timer: bool
    triggers_angry_lock: bool


def clamp_mood_score(score):
    return max(0.0, min(100.0, float(score)))


def derive_mood_state(mood_score):
    if mood_score < 20:
        return "depressed"
    if mood_score < 50:
        return "unhappy"
    return "normal"


def natural_mood_update_is_paused(*, activity_kind, activity_active):
    return bool(
        activity_active
        and str(activity_kind or "")
        in NATURAL_MOOD_PAUSED_ACTIVITY_KINDS
    )


def _clamp_unit(value):
    return max(0.0, min(1.0, float(value)))


def _child_adult_separation(nearest_adult_distance, has_adult_nearby):
    if has_adult_nearby:
        return 0.0
    if nearest_adult_distance is None:
        return 1.0
    distance = max(0.0, float(nearest_adult_distance))
    span = (
        MOOD_ADULT_FULL_SEPARATION_DISTANCE_PX
        - MOOD_ADULT_COMFORT_DISTANCE_PX
    )
    return _clamp_unit(
        (distance - MOOD_ADULT_COMFORT_DISTANCE_PX) / span
    )


def _interpolate(low, high, roll):
    return float(low) + (float(high) - float(low)) * _clamp_unit(roll)


def compute_mood_update(
    current_score,
    lonely_timer,
    is_adult,
    nearby_count,
    has_adult_nearby,
    noise=0.0,
    climate_key=None,
    change_roll=0.0,
    direction_roll=None,
    magnitude_roll=None,
    nearest_adult_distance=None,
):
    recovery = 0.5 + (0.0 if is_adult else 0.5)
    next_lonely_timer = int(lonely_timer)

    if nearby_count > 0:
        recovery += 0.5
        if not is_adult and has_adult_nearby:
            recovery += 2.0

    if not is_adult:
        if nearby_count == 0:
            next_lonely_timer += 3
            if next_lonely_timer >= 10:
                recovery -= 2.0
        else:
            next_lonely_timer = 0

    profile = MOOD_CLIMATE_PROFILES.get(str(climate_key or ""))
    if profile is None:
        # Keep this pure helper backward-compatible for callers that do not
        # opt into a climate. Runtime always supplies the configured climate.
        mood_delta = recovery + float(noise)
    else:
        if _clamp_unit(change_roll) >= profile.change_chance:
            mood_delta = 0.0
        else:
            if direction_roll is None:
                direction_roll = (float(noise) + 1.0) / 2.0
            if magnitude_roll is None:
                magnitude_roll = abs(float(noise))

            separation = (
                _child_adult_separation(
                    nearest_adult_distance,
                    has_adult_nearby,
                )
                if not is_adult else
                0.0
            )
            adult_is_comfortably_close = bool(
                has_adult_nearby
                or (
                    nearest_adult_distance is not None
                    and float(nearest_adult_distance)
                    <= MOOD_ADULT_COMFORT_DISTANCE_PX
                )
            )
            negative_chance = profile.negative_chance
            positive_multiplier = 1.0
            if nearby_count > 0:
                negative_chance -= profile.companion_relief
                positive_multiplier += profile.companion_positive_bonus
            if not is_adult:
                if adult_is_comfortably_close:
                    negative_chance -= profile.adult_comfort_relief
                    positive_multiplier += (
                        profile.adult_comfort_positive_bonus
                    )
                else:
                    negative_chance += (
                        profile.child_separation_chance_bonus * separation
                    )
                if float(current_score) < 50.0:
                    # Low-band children retain some natural resilience even
                    # when alone, while a nearby adult provides the full
                    # stabilising effect. This lets balanced mood visit low
                    # without turning ordinary solitude into an immediate
                    # severe-state trigger.
                    child_recovery_bias = profile.child_low_recovery_bias * (
                        1.0 if adult_is_comfortably_close else 0.75
                    )
                    negative_chance -= child_recovery_bias
                    positive_multiplier += child_recovery_bias
                if nearby_count == 0 and next_lonely_timer >= 10:
                    negative_chance += (
                        profile.child_lonely_chance_bonus
                    )
            elif float(current_score) < 50.0:
                adult_recovery_bias = profile.adult_low_recovery_bias
                if float(current_score) < 20.0:
                    adult_recovery_bias += (
                        profile.adult_severe_recovery_bias
                    )
                negative_chance -= adult_recovery_bias
                positive_multiplier += adult_recovery_bias

            negative_chance = max(0.02, min(0.98, negative_chance))
            if _clamp_unit(direction_roll) < negative_chance:
                negative_magnitude = _interpolate(
                    profile.negative_delta_min,
                    profile.negative_delta_max,
                    magnitude_roll,
                )
                if is_adult:
                    negative_magnitude *= (
                        profile.adult_negative_magnitude_scale
                    )
                else:
                    negative_magnitude *= (
                        1.0
                        + separation
                        * profile.child_separation_magnitude_bonus
                    )
                    if nearby_count == 0 and next_lonely_timer >= 10:
                        negative_magnitude *= (
                            profile.child_lonely_magnitude_scale
                        )
                mood_delta = -negative_magnitude
            else:
                mood_delta = _interpolate(
                    profile.positive_delta_min,
                    profile.positive_delta_max,
                    magnitude_roll,
                ) * positive_multiplier
    next_score = clamp_mood_score(float(current_score) + mood_delta)
    return MoodUpdate(
        mood_score=next_score,
        mood_state=derive_mood_state(next_score),
        lonely_timer=next_lonely_timer,
    )


def decide_release_interaction(duration, click_count, click_threshold=5, click_duration=0.2, long_hold_duration=5.0):
    duration = float(duration)
    current_click_count = int(click_count)

    if duration < click_duration:
        next_click_count = current_click_count + 1
        triggers_angry_lock = next_click_count >= int(click_threshold)
        return ReleaseDecision(
            kind=CLICK_RELEASE,
            next_click_count=next_click_count,
            mood_delta=-60.0 if triggers_angry_lock else 8.0,
            starts_click_reset_timer=True,
            triggers_angry_lock=triggers_angry_lock,
        )

    if duration > long_hold_duration:
        return ReleaseDecision(
            kind=LONG_HOLD_RELEASE,
            next_click_count=current_click_count,
            mood_delta=-25.0,
            starts_click_reset_timer=False,
            triggers_angry_lock=False,
        )

    return ReleaseDecision(
        kind=DRAG_RELEASE,
        next_click_count=current_click_count,
        mood_delta=0.0,
        starts_click_reset_timer=False,
        triggers_angry_lock=False,
    )


def decide_tick_phase(dragging, window_perch_handled, window_flight_handled, vertical_velocity):
    if dragging:
        return TICK_PHASE_DRAGGING
    if window_perch_handled:
        return TICK_PHASE_WINDOW_PERCH
    if window_flight_handled:
        return TICK_PHASE_WINDOW_FLIGHT
    if float(vertical_velocity) == 0.0:
        return TICK_PHASE_RUN_AI
    return TICK_PHASE_AIRBORNE


def decide_initial_ai_phase(is_angry_locked, is_recovering, recovery_expired):
    if is_angry_locked:
        return AI_PHASE_ANGRY_LOCKED
    if is_recovering:
        if recovery_expired:
            return AI_PHASE_RECOVERY_FINISHED
        return AI_PHASE_RECOVERY_ACTIVE
    return AI_PHASE_NORMAL


def decide_followup_ai_phase(care_lock_maintained, care_behavior_handled, social_behavior_handled):
    if care_lock_maintained:
        return AI_FOLLOWUP_CARE_LOCK
    if care_behavior_handled:
        return AI_FOLLOWUP_CARE
    if social_behavior_handled:
        return AI_FOLLOWUP_SOCIAL
    return AI_FOLLOWUP_RANDOM
