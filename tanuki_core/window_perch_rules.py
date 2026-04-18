from dataclasses import dataclass


@dataclass(frozen=True)
class WindowPerchModeDecision:
    mode: str
    state: str
    state_timer: int
    direction: int
    use_walk_animation: bool


@dataclass(frozen=True)
class WindowPerchWalkDecision:
    next_offset: int
    direction: int
    mode: str
    state: str
    state_timer: int | None


def decide_window_perch_mode(
    *,
    max_offset,
    offset_x,
    direction,
    has_walk_candidates,
    move_roll,
    flip_roll,
    move_timer,
    idle_timer,
):
    can_walk = bool(has_walk_candidates) and int(max_offset) >= 30
    next_direction = int(direction) if int(direction) != 0 else 1
    if can_walk and float(move_roll) < 0.62:
        if int(offset_x) <= 5:
            next_direction = 1
        elif int(offset_x) >= max(5, int(max_offset) - 5):
            next_direction = -1
        elif float(flip_roll) < 0.5:
            next_direction *= -1
        return WindowPerchModeDecision(
            mode="move",
            state="move",
            state_timer=int(move_timer),
            direction=next_direction,
            use_walk_animation=True,
        )

    if float(flip_roll) < 0.35:
        next_direction *= -1
    return WindowPerchModeDecision(
        mode="idle",
        state="idle",
        state_timer=int(idle_timer),
        direction=next_direction,
        use_walk_animation=False,
    )


def advance_window_perch_walk(*, offset_x, direction, step, max_offset, boundary_idle_timer):
    next_offset = int(offset_x) + (int(step) * int(direction))
    next_direction = int(direction) if int(direction) != 0 else 1
    if next_offset <= 0:
        return WindowPerchWalkDecision(
            next_offset=0,
            direction=1,
            mode="idle",
            state="idle",
            state_timer=int(boundary_idle_timer),
        )
    if next_offset >= int(max_offset):
        return WindowPerchWalkDecision(
            next_offset=int(max_offset),
            direction=-1,
            mode="idle",
            state="idle",
            state_timer=int(boundary_idle_timer),
        )
    return WindowPerchWalkDecision(
        next_offset=int(next_offset),
        direction=next_direction,
        mode="move",
        state="move",
        state_timer=None,
    )
