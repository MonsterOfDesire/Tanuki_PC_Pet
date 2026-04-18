import unittest
from dataclasses import dataclass

from tanuki_core.window_surface_selector import (
    WindowActorSnapshot,
    find_drop_surface,
    find_flight_surface,
)


@dataclass(frozen=True)
class FakePoint:
    _x: int
    _y: int

    def x(self):
        return self._x

    def y(self):
        return self._y


@dataclass(frozen=True)
class FakeRect:
    x_value: int
    y_value: int
    width_value: int
    height_value: int

    def left(self):
        return self.x_value

    def top(self):
        return self.y_value

    def width(self):
        return self.width_value

    def height(self):
        return self.height_value

    def right(self):
        return self.x_value + self.width_value - 1

    def bottom(self):
        return self.y_value + self.height_value - 1

    def center(self):
        return FakePoint(
            self.x_value + (self.width_value // 2),
            self.y_value + (self.height_value // 2),
        )


@dataclass(frozen=True)
class FakeSurface:
    hwnd: int
    rect: FakeRect

    def perch_y(self, actor_height):
        return self.rect.top() - actor_height

    def contains_x(self, x):
        return self.rect.left() <= int(x) <= self.rect.right()


class FakeActor:
    def __init__(self, rect, width, height):
        self._rect = rect
        self._width = width
        self._height = height

    def geometry(self):
        return self._rect

    def width(self):
        return self._width

    def height(self):
        return self._height


class FirstChoiceRng:
    def choices(self, population, weights, k):
        return [population[0]]


class SurfaceSelectorTests(unittest.TestCase):
    def setUp(self):
        self.actor = WindowActorSnapshot(
            rect=FakeRect(150, 210, 80, 80),
            width=80,
            height=80,
        )

    def test_actor_snapshot_from_actor_uses_geometry_width_and_height(self):
        actor = FakeActor(FakeRect(10, 20, 90, 100), 90, 100)

        snapshot = WindowActorSnapshot.from_actor(actor)

        self.assertEqual(snapshot.rect.top(), 20)
        self.assertEqual(snapshot.width, 90)
        self.assertEqual(snapshot.height, 100)

    def test_actor_snapshot_from_actor_returns_existing_snapshot(self):
        snapshot = WindowActorSnapshot.from_actor(self.actor)

        self.assertIs(snapshot, self.actor)

    def test_find_drop_surface_selects_matching_surface_with_visible_anchor(self):
        target = FakeSurface(1, FakeRect(120, 250, 260, 120))
        far = FakeSurface(2, FakeRect(500, 250, 260, 120))

        selected = find_drop_surface(
            self.actor,
            [far, target],
            can_actor_perch_on_surface=lambda surface: surface.hwnd == target.hwnd,
            get_surface_visible_center_x=lambda surface, actor_width=0, preferred_center_x=None, exact=False: surface.rect.center().x(),
            snap_top_tolerance=110,
            snap_depth_limit=70,
        )

        self.assertIs(selected, target)

    def test_find_drop_surface_returns_none_when_actor_is_outside_snap_band(self):
        target = FakeSurface(1, FakeRect(120, 400, 260, 120))

        selected = find_drop_surface(
            self.actor,
            [target],
            can_actor_perch_on_surface=lambda surface: True,
            get_surface_visible_center_x=lambda surface, actor_width=0, preferred_center_x=None, exact=False: surface.rect.center().x(),
            snap_top_tolerance=110,
            snap_depth_limit=70,
        )

        self.assertIsNone(selected)

    def test_find_flight_surface_prefers_best_scored_candidate(self):
        best = FakeSurface(1, FakeRect(120, 40, 260, 120))
        farther = FakeSurface(2, FakeRect(720, 20, 260, 120))

        selected = find_flight_surface(
            self.actor,
            [farther, best],
            can_actor_perch_on_surface=lambda surface: True,
            get_surface_visible_center_x=lambda surface, actor_width=0, preferred_center_x=None, exact=False: surface.rect.center().x(),
            rng=FirstChoiceRng(),
        )

        self.assertIs(selected, best)

    def test_find_flight_surface_returns_none_when_no_surface_is_high_enough(self):
        low_surface = FakeSurface(1, FakeRect(120, 280, 260, 120))

        selected = find_flight_surface(
            self.actor,
            [low_surface],
            can_actor_perch_on_surface=lambda surface: True,
            get_surface_visible_center_x=lambda surface, actor_width=0, preferred_center_x=None, exact=False: surface.rect.center().x(),
            rng=FirstChoiceRng(),
        )

        self.assertIsNone(selected)


if __name__ == "__main__":
    unittest.main()
