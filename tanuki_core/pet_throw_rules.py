from __future__ import annotations

from dataclasses import dataclass
import math


DRAG_MOTION_SAMPLE_WINDOW_SECONDS = 0.14
DRAG_MOTION_MAX_SAMPLES = 8
DRAG_MOTION_MIN_SPAN_SECONDS = 0.015
THROW_MIN_POINTER_SPEED_PX_PER_SECOND = 180.0
THROW_POINTER_TO_STEP_SCALE = 0.020
THROW_MAX_HORIZONTAL_SPEED_PER_STEP = 26.0
THROW_MAX_VERTICAL_SPEED_PER_STEP = 22.0
THROW_HORIZONTAL_FRICTION = 0.94
THROW_EDGE_RESTITUTION = 0.32
THROW_STOP_SPEED_PER_STEP = 0.25


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
    if next_samples and sample[0] == next_samples[-1][0]:
        next_samples[-1] = sample
    else:
        next_samples.append(sample)
    cutoff = sample[0] - max(0.01, float(window_seconds))
    next_samples = [item for item in next_samples if item[0] >= cutoff]
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
    min_pointer_speed=THROW_MIN_POINTER_SPEED_PX_PER_SECOND,
):
    recent = tuple(samples or ())
    if len(recent) < 2:
        return ThrowLaunch(False)
    span = float(recent[-1][0]) - float(recent[0][0])
    if span < DRAG_MOTION_MIN_SPAN_SECONDS:
        return ThrowLaunch(False)
    pointer_vx = _least_squares_velocity(recent, 1)
    pointer_vy = _least_squares_velocity(recent, 2)
    if math.hypot(pointer_vx, pointer_vy) < float(min_pointer_speed):
        return ThrowLaunch(False)
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


def advance_horizontal_throw(
    *,
    current_x,
    velocity_x,
    remainder_x,
    left_bound,
    right_bound,
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
    next_velocity *= THROW_HORIZONTAL_FRICTION
    if abs(next_velocity) < THROW_STOP_SPEED_PER_STEP:
        next_velocity = 0.0
        next_remainder = 0.0
    return HorizontalThrowStep(
        x=next_x,
        velocity_x=next_velocity,
        remainder_x=next_remainder,
        active=next_velocity != 0.0,
    )
