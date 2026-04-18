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


@dataclass(frozen=True)
class MoodUpdate:
    mood_score: float
    mood_state: str
    lonely_timer: int


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


def compute_mood_update(current_score, lonely_timer, is_adult, nearby_count, has_adult_nearby, noise=0.0):
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

    next_score = clamp_mood_score(float(current_score) + recovery + float(noise))
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
