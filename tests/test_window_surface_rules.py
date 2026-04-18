import unittest
from dataclasses import dataclass

from tanuki_core.window_surface_rules import (
    build_surface_center_candidates,
    can_actor_perch_on_surface,
    get_surface_visible_center_x,
    is_surface_perch_allowed,
    is_surface_top_segment_visible,
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


class SurfaceRuleTests(unittest.TestCase):
    def test_full_screen_like_surface_is_not_allowed_for_perching(self):
        screen_rect = FakeRect(0, 0, 1920, 1080)
        blocked_surface = FakeRect(0, 0, 1910, 1070)
        regular_surface = FakeRect(80, 120, 1200, 700)

        self.assertFalse(is_surface_perch_allowed(blocked_surface, screen_rect))
        self.assertTrue(is_surface_perch_allowed(regular_surface, screen_rect))

    def test_actor_perch_height_must_leave_enough_visible_area(self):
        screen_rect = FakeRect(0, 0, 1920, 1080)
        low_surface = FakeSurface(1, FakeRect(100, 40, 500, 200))
        safe_surface = FakeSurface(2, FakeRect(100, 160, 500, 200))

        self.assertFalse(can_actor_perch_on_surface(low_surface, screen_rect, actor_height=120))
        self.assertTrue(can_actor_perch_on_surface(safe_surface, screen_rect, actor_height=120))

    def test_build_surface_center_candidates_clamps_preferred_and_deduplicates(self):
        surface_rect = FakeRect(0, 0, 300, 100)

        candidates = build_surface_center_candidates(
            surface_rect,
            actor_width=80,
            preferred_center_x=-50,
            exact=False,
            top_edge_inset=18,
        )

        self.assertGreaterEqual(len(candidates), 2)
        self.assertEqual(candidates[0], 40)
        self.assertEqual(len(candidates), len(set(candidates)))

    def test_top_segment_visible_checks_probe_points_against_top_surface(self):
        surface = FakeSurface(11, FakeRect(100, 100, 300, 160))
        screen_rect = FakeRect(0, 0, 1920, 1080)

        def visible_top(_x, _y):
            return surface

        def blocked_top(_x, _y):
            return FakeSurface(99, FakeRect(100, 100, 300, 160))

        self.assertTrue(
            is_surface_top_segment_visible(
                surface,
                center_x=220,
                screen_rect=screen_rect,
                get_top_surface_at_point=visible_top,
                actor_width=80,
            )
        )
        self.assertFalse(
            is_surface_top_segment_visible(
                surface,
                center_x=220,
                screen_rect=screen_rect,
                get_top_surface_at_point=blocked_top,
                actor_width=80,
            )
        )

    def test_visible_center_falls_back_to_next_candidate_when_preferred_is_blocked(self):
        surface = FakeSurface(11, FakeRect(100, 100, 300, 160))
        center_x = surface.rect.center().x()

        def only_center_visible(_surface, probe_x, actor_width=0):
            return probe_x == center_x

        selected = get_surface_visible_center_x(
            surface,
            surface_allowed=True,
            is_top_segment_visible=only_center_visible,
            actor_width=80,
            preferred_center_x=120,
            exact=False,
        )

        self.assertEqual(selected, center_x)


if __name__ == "__main__":
    unittest.main()
