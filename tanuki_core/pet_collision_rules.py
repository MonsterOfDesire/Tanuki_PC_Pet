import math
from dataclasses import dataclass


@dataclass(frozen=True)
class CollisionSnapshot:
    center_x: float
    center_y: float
    radius: float
    mass: float
    is_adult: bool = False


@dataclass(frozen=True)
class CollisionResolution:
    delta_x: int
    colliding_adult_indices: tuple[int, ...]


def compute_collision_resolution(subject, neighbors, mood_score):
    repel_x = 0.0
    colliding_adult_indices = []
    repel_weight = 0.2 if mood_score >= 20 else 0.05

    for index, other in enumerate(neighbors):
        dist_x = subject.center_x - other.center_x
        dist_y = subject.center_y - other.center_y
        dist = math.hypot(dist_x, dist_y)
        effective_radius = subject.radius + other.radius
        if dist >= effective_radius:
            continue
        overlap = effective_radius - dist
        if overlap <= 5.0:
            continue
        total_mass = subject.mass + other.mass
        if total_mass <= 0:
            continue
        repel_x += (dist_x / (dist if dist > 0 else 1)) * overlap * (other.mass / total_mass)
        if not subject.is_adult and other.is_adult:
            colliding_adult_indices.append(index)

    if abs(repel_x) <= 0.5:
        delta_x = 0
    else:
        delta_x = int(repel_x * repel_weight)

    return CollisionResolution(
        delta_x=delta_x,
        colliding_adult_indices=tuple(colliding_adult_indices),
    )
