from dataclasses import dataclass


HARD_LANDING_IMPACT_THRESHOLD = 15.0
SOFT_LANDING_IMPACT_THRESHOLD = 3.0
HARD_LANDING_REACTION_MOODS = ("scared", "exhausted", "cry")


@dataclass(frozen=True)
class GravityStepResult:
    next_y: int
    next_vy: float
    fall_origin_y: int | None
    mood_penalty: float = 0.0
    reaction_moods: tuple[str, ...] = ()


def update_fall_origin(current_y, floor_top_y, fall_origin_y):
    if current_y >= floor_top_y:
        return None
    if fall_origin_y is None:
        return int(current_y)
    return min(int(fall_origin_y), int(current_y))


def compute_fall_mood_penalty(fall_distance, max_fall_distance):
    fall_distance = max(0.0, float(fall_distance))
    max_fall_distance = max(1.0, float(max_fall_distance))
    fall_ratio = min(1.0, fall_distance / max_fall_distance)
    return min(70.0, 8.0 + (75.0 * fall_ratio))


def compute_gravity_step(current_y, current_vy, gravity, floor_top_y, bounce, fall_origin_y, max_fall_distance):
    tracked_origin = update_fall_origin(current_y, floor_top_y, fall_origin_y)
    if current_vy != 0 or current_y < floor_top_y:
        next_vy = current_vy + gravity
        next_y = current_y + int(next_vy)
        if next_y >= floor_top_y:
            impact = next_vy
            if abs(impact) > HARD_LANDING_IMPACT_THRESHOLD:
                fall_distance = max(0.0, floor_top_y - (tracked_origin if tracked_origin is not None else current_y))
                return GravityStepResult(
                    next_y=int(floor_top_y),
                    next_vy=impact * bounce,
                    fall_origin_y=None,
                    mood_penalty=compute_fall_mood_penalty(fall_distance, max_fall_distance),
                    reaction_moods=HARD_LANDING_REACTION_MOODS,
                )
            if abs(impact) > SOFT_LANDING_IMPACT_THRESHOLD:
                return GravityStepResult(
                    next_y=int(floor_top_y),
                    next_vy=next_vy * -0.4,
                    fall_origin_y=None,
                )
            return GravityStepResult(
                next_y=int(floor_top_y),
                next_vy=0.0,
                fall_origin_y=None,
            )
        return GravityStepResult(
            next_y=int(next_y),
            next_vy=next_vy,
            fall_origin_y=tracked_origin,
        )

    if current_y > floor_top_y:
        return GravityStepResult(
            next_y=int(floor_top_y),
            next_vy=0.0,
            fall_origin_y=None,
        )

    return GravityStepResult(
        next_y=int(current_y),
        next_vy=current_vy,
        fall_origin_y=None,
    )
