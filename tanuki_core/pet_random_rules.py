from dataclasses import dataclass


SEVERE_RANDOM_DIRECTION_FLIP_CHANCE = 0.25
NORMAL_RANDOM_DIRECTION_FLIP_CHANCE = 0.3
RANDOM_STUCK_REVERSE_THRESHOLD = 60
RANDOM_MOVE_PURPOSE_SPEED_THRESHOLD = 0.8
RANDOM_CONTEXT = "random"
SIDE_READY_FOLLOWUP_CONTEXT = "side_ready_followup"
SIDE_READY_FOLLOWUP_CHANCE = 0.10
SIDE_READY_FOLLOWUP_MIN_HOLD_STEPS = 60
SIDE_READY_FOLLOWUP_ACTIONS = frozenset({
    "side_stand",
    "side_stand_cheer",
})


@dataclass(frozen=True)
class RandomStateTransition:
    next_state: str
    next_state_timer: int
    clear_current_purpose: bool = True
    reset_stationary_mode: bool = True
    flip_direction: bool = False


@dataclass(frozen=True)
class RandomStuckResolution:
    next_stuck_count: int
    flip_direction: bool = False
    next_state_timer: int | None = None


def should_refresh_severe_random_state(current_mood_tag, severe_moods, state_timer):
    return current_mood_tag not in severe_moods or state_timer <= 0


def build_random_state_transition(next_state, next_state_timer, flip_roll, flip_threshold):
    return RandomStateTransition(
        next_state=next_state,
        next_state_timer=next_state_timer,
        flip_direction=flip_roll < flip_threshold,
    )


def resolve_random_stuck_behavior(stationary_move_mode, position_delta, stuck_count, recovery_state_timer):
    if stationary_move_mode:
        return RandomStuckResolution(next_stuck_count=0)

    if abs(position_delta) < 0.5:
        next_stuck_count = stuck_count + 1
    else:
        next_stuck_count = max(0, stuck_count - 1)

    if next_stuck_count > RANDOM_STUCK_REVERSE_THRESHOLD:
        return RandomStuckResolution(
            next_stuck_count=0,
            flip_direction=True,
            next_state_timer=recovery_state_timer,
        )

    return RandomStuckResolution(next_stuck_count=next_stuck_count)


def derive_random_visual_purpose(state, base_speed):
    if state == "move" and base_speed > RANDOM_MOVE_PURPOSE_SPEED_THRESHOLD:
        return "move"
    return "idle"


def extend_random_state_timer(state_timer, hold_timer):
    return max(int(state_timer), int(hold_timer))


def choose_idle_animation_context(
    *,
    side_ready_followup_armed,
    roll,
    followup_chance=SIDE_READY_FOLLOWUP_CHANCE,
):
    """Choose the next manifest context after a side-ready idle pose."""
    if not bool(side_ready_followup_armed):
        return RANDOM_CONTEXT
    chance = max(0.0, min(1.0, float(followup_chance)))
    if float(roll) < chance:
        return SIDE_READY_FOLLOWUP_CONTEXT
    return RANDOM_CONTEXT


def is_visible_side_ready_followup(purpose, action_tag):
    """Return whether the applied visual is a standing follow-up pose."""
    return (
        str(purpose or "") == "idle"
        and str(action_tag or "") in SIDE_READY_FOLLOWUP_ACTIONS
    )


def is_side_ready_followup_eligible(
    name,
    *,
    side_ready_followup_armed,
    current_action_tag,
    current_frames,
):
    """Return whether a side-ready pose may be consumed by its next resolver."""
    return (
        str(name or "") == "Tsurumaru Tsuyoshi"
        and bool(side_ready_followup_armed)
        and str(current_action_tag or "") == "side_ready"
        and bool(current_frames)
    )


def get_idle_action_override(name, *, current_purpose, current_action_tag, next_purpose, next_action_tag):
    if name != "Tsurumaru Tsuyoshi":
        return ()
    if next_purpose != "idle" or next_action_tag not in SIDE_READY_FOLLOWUP_ACTIONS:
        return ()
    if current_purpose == "idle" and current_action_tag == "side_ready":
        return ()
    return ("side_ready", "side", "stand")
