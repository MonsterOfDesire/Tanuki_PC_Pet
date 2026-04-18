import random
from dataclasses import dataclass


@dataclass(frozen=True)
class WindowActorSnapshot:
    rect: object
    width: int
    height: int

    @classmethod
    def from_actor(cls, actor):
        if isinstance(actor, cls):
            return actor
        return cls(
            rect=actor.geometry(),
            width=actor.width(),
            height=actor.height(),
        )

    @property
    def center_x(self):
        return self.rect.center().x()

    @property
    def top(self):
        return self.rect.top()

    @property
    def bottom(self):
        return self.rect.bottom()

    @property
    def y(self):
        return self.rect.top()


def find_drop_surface(
    actor,
    surfaces,
    can_actor_perch_on_surface,
    get_surface_visible_center_x,
    snap_top_tolerance,
    snap_depth_limit,
):
    probe_x = actor.center_x
    for surface in surfaces:
        if not can_actor_perch_on_surface(surface):
            continue
        if not surface.contains_x(probe_x):
            continue
        top_y = surface.rect.top()
        if actor.bottom < (top_y - snap_top_tolerance):
            continue
        if actor.bottom > (top_y + snap_depth_limit):
            continue
        if actor.top > (top_y + snap_depth_limit):
            continue
        if not get_surface_visible_center_x(
            surface,
            actor_width=actor.width,
            preferred_center_x=probe_x,
            exact=True,
        ):
            continue
        return surface
    return None


def find_flight_surface(
    actor,
    surfaces,
    can_actor_perch_on_surface,
    get_surface_visible_center_x,
    rng=None,
):
    rng = rng or random
    candidates = []
    for surface in surfaces:
        if not can_actor_perch_on_surface(surface):
            continue
        if surface.rect.width() < max(160, int(actor.width * 0.55)):
            continue
        anchor_center_x = get_surface_visible_center_x(
            surface,
            actor_width=actor.width,
            preferred_center_x=actor.center_x,
        )
        if anchor_center_x is None:
            continue
        perch_y = surface.perch_y(actor.height)
        if perch_y >= actor.y - 30:
            continue
        dx = abs(anchor_center_x - actor.center_x)
        dy = abs(perch_y - actor.y)
        score = dx + (dy * 0.8)
        candidates.append((score, surface))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0])
    top_candidates = candidates[: min(3, len(candidates))]
    weights = [1.0 / max(1.0, score + 1.0) for score, _surface in top_candidates]
    return rng.choices(
        [surface for _score, surface in top_candidates],
        weights=weights,
        k=1,
    )[0]
