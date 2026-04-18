from dataclasses import dataclass


SEVERE_RANDOM_DIRECTION_FLIP_CHANCE = 0.25
NORMAL_RANDOM_DIRECTION_FLIP_CHANCE = 0.3
RANDOM_STUCK_REVERSE_THRESHOLD = 60
RANDOM_MOVE_PURPOSE_SPEED_THRESHOLD = 0.8


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
