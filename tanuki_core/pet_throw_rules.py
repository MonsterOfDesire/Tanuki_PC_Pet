from __future__ import annotations

from dataclasses import dataclass
import math


DRAG_MOTION_SAMPLE_WINDOW_SECONDS = 0.30
DRAG_MOTION_MAX_SAMPLES = 12
DRAG_MOTION_MIN_SPAN_SECONDS = 0.015
THROW_RELEASE_GRACE_SECONDS = 0.22
THROW_MIN_POINTER_SPEED_PX_PER_SECOND = 120.0
THROW_POINTER_TO_STEP_SCALE = 0.040
THROW_MAX_HORIZONTAL_SPEED_PER_STEP = 34.0
THROW_MAX_VERTICAL_SPEED_PER_STEP = 28.0
THROW_HORIZONTAL_FRICTION = 0.98
THROW_ACTIVE_GRAVITY_SCALE = 0.72
THROW_GROUND_SLOWDOWN_SPEED_PER_STEP = 8.0
THROW_GROUND_FRICTION = 0.86
THROW_GROUND_STOP_SPEED_PER_STEP = 0.5
THROW_EDGE_RESTITUTION = 0.32
THROW_STOP_SPEED_PER_STEP = 0.25
DRAG_FOLLOW_TIMER_MS = 16
DRAG_FOLLOW_STIFFNESS = 120.0
DRAG_FOLLOW_DAMPING = 19.0
DRAG_FOLLOW_MAX_SPEED_PX_PER_SECOND = 2600.0
DRAG_FOLLOW_SNAP_DISTANCE_PX = 0.75
DRAG_FOLLOW_SNAP_SPEED_PX_PER_SECOND = 15.0


@dataclass(frozen=True)
class ThrowLaunch:
    active: bool
    velocity_x: float = 0.0
    velocity_y: float = 0.0


@dataclass(frozen=True)
class HorizontalThrowStep:
    x: int
    velocity_x: float
    remainder_x: float
    active: bool


@dataclass(frozen=True)
class DragFollowStep:
    x: float
    y: float
    velocity_x: float
    velocity_y: float


def append_drag_motion_sample(
    samples,
    *,
    timestamp,
    x,
    y,
    window_seconds=DRAG_MOTION_SAMPLE_WINDOW_SECONDS,
    max_samples=DRAG_MOTION_MAX_SAMPLES,
):
    """Return a short, monotonically ordered cursor history."""
    next_samples = list(samples or ())
    sample = (float(timestamp), float(x), float(y))
    if next_samples and sample[0] < next_samples[-1][0]:
        next_samples = []
    if (
        next_samples
        and sample[1] == next_samples[-1][1]
        and sample[2] == next_samples[-1][2]
    ):
        # A stationary release event must not erase the last real movement
        # timestamp.  The resolver uses it to decide whether a flick is fresh.
        return tuple(next_samples[-max(2, int(max_samples)):])
    if next_samples and sample[0] == next_samples[-1][0]:
        next_samples[-1] = sample
    else:
        next_samples.append(sample)
    cutoff = sample[0] - max(0.01, float(window_seconds))
    older = [item for item in next_samples if item[0] < cutoff]
    recent = [item for item in next_samples if item[0] >= cutoff]
    # Retain one predecessor so sparse/compressed UI motion events still have
    # a velocity baseline instead of collapsing to a single release point.
    next_samples = ((older[-1],) if older else ()) + tuple(recent)
    return tuple(next_samples[-max(2, int(max_samples)):])


def _least_squares_velocity(samples, axis_index):
    timestamps = [item[0] for item in samples]
    values = [item[axis_index] for item in samples]
    mean_t = sum(timestamps) / len(timestamps)
    mean_value = sum(values) / len(values)
    denominator = sum((timestamp - mean_t) ** 2 for timestamp in timestamps)
    if denominator <= 1e-12:
        return 0.0
    return sum(
        (timestamp - mean_t) * (value - mean_value)
        for timestamp, value in zip(timestamps, values)
    ) / denominator


def resolve_throw_launch(
    samples,
    *,
    released_at=None,
    release_grace_seconds=THROW_RELEASE_GRACE_SECONDS,
    min_pointer_speed=THROW_MIN_POINTER_SPEED_PX_PER_SECOND,
    carried_velocity=None,
):
    if carried_velocity is not None:
        pointer_vx = float(carried_velocity[0])
        pointer_vy = float(carried_velocity[1])
        if math.hypot(pointer_vx, pointer_vy) < float(min_pointer_speed):
            return ThrowLaunch(False)
        return _bounded_throw_launch(pointer_vx, pointer_vy)
    recent = tuple(samples or ())
    if len(recent) < 2:
        return ThrowLaunch(False)
    if (
        released_at is not None
        and float(released_at) - float(recent[-1][0])
        > max(0.0, float(release_grace_seconds))
    ):
        return ThrowLaunch(False)
    span = float(recent[-1][0]) - float(recent[0][0])
    if span < DRAG_MOTION_MIN_SPAN_SECONDS:
        return ThrowLaunch(False)
    pointer_vx = _least_squares_velocity(recent, 1)
    pointer_vy = _least_squares_velocity(recent, 2)
    if math.hypot(pointer_vx, pointer_vy) < float(min_pointer_speed):
        return ThrowLaunch(False)
    return _bounded_throw_launch(pointer_vx, pointer_vy)


def _bounded_throw_launch(pointer_vx, pointer_vy):
    return ThrowLaunch(
        True,
        max(
            -THROW_MAX_HORIZONTAL_SPEED_PER_STEP,
            min(
                THROW_MAX_HORIZONTAL_SPEED_PER_STEP,
                pointer_vx * THROW_POINTER_TO_STEP_SCALE,
            ),
        ),
        max(
            -THROW_MAX_VERTICAL_SPEED_PER_STEP,
            min(
                THROW_MAX_VERTICAL_SPEED_PER_STEP,
                pointer_vy * THROW_POINTER_TO_STEP_SCALE,
            ),
        ),
    )


def advance_drag_follow(
    *,
    current_x,
    current_y,
    target_x,
    target_y,
    velocity_x,
    velocity_y,
    elapsed_seconds,
):
    """Advance a damped spring toward the cursor-defined drag target."""
    dt = max(0.001, min(0.035, float(elapsed_seconds)))
    dx = float(target_x) - float(current_x)
    dy = float(target_y) - float(current_y)
    next_vx = (
        float(velocity_x)
        + (DRAG_FOLLOW_STIFFNESS * dx - DRAG_FOLLOW_DAMPING * float(velocity_x))
        * dt
    )
    next_vy = (
        float(velocity_y)
        + (DRAG_FOLLOW_STIFFNESS * dy - DRAG_FOLLOW_DAMPING * float(velocity_y))
        * dt
    )
    speed = math.hypot(next_vx, next_vy)
    if speed > DRAG_FOLLOW_MAX_SPEED_PX_PER_SECOND:
        scale = DRAG_FOLLOW_MAX_SPEED_PX_PER_SECOND / speed
        next_vx *= scale
        next_vy *= scale
    next_x = float(current_x) + next_vx * dt
    next_y = float(current_y) + next_vy * dt
    if (
        math.hypot(float(target_x) - next_x, float(target_y) - next_y)
        <= DRAG_FOLLOW_SNAP_DISTANCE_PX
        and math.hypot(next_vx, next_vy)
        <= DRAG_FOLLOW_SNAP_SPEED_PX_PER_SECOND
    ):
        return DragFollowStep(
            x=float(target_x),
            y=float(target_y),
            velocity_x=0.0,
            velocity_y=0.0,
        )
    return DragFollowStep(
        x=next_x,
        y=next_y,
        velocity_x=next_vx,
        velocity_y=next_vy,
    )


def advance_horizontal_throw(
    *,
    current_x,
    velocity_x,
    remainder_x,
    left_bound,
    right_bound,
    grounded=False,
):
    proposed = float(current_x) + float(remainder_x) + float(velocity_x)
    next_x = int(round(proposed))
    next_remainder = proposed - next_x
    next_velocity = float(velocity_x)
    if next_x < int(left_bound):
        next_x = int(left_bound)
        next_remainder = 0.0
        next_velocity = abs(next_velocity) * THROW_EDGE_RESTITUTION
    elif next_x > int(right_bound):
        next_x = int(right_bound)
        next_remainder = 0.0
        next_velocity = -abs(next_velocity) * THROW_EDGE_RESTITUTION
    low_speed_on_ground = (
        bool(grounded)
        and abs(next_velocity) <= THROW_GROUND_SLOWDOWN_SPEED_PER_STEP
    )
    next_velocity *= (
        THROW_GROUND_FRICTION
        if low_speed_on_ground
        else THROW_HORIZONTAL_FRICTION
    )
    stop_speed = (
        THROW_GROUND_STOP_SPEED_PER_STEP
        if low_speed_on_ground
        else THROW_STOP_SPEED_PER_STEP
    )
    if abs(next_velocity) < stop_speed:
        next_velocity = 0.0
        next_remainder = 0.0
    return HorizontalThrowStep(
        x=next_x,
        velocity_x=next_velocity,
        remainder_x=next_remainder,
        active=next_velocity != 0.0,
    )
