import unittest

from tanuki_core.pet_windowing_effects import WINDOWING_EFFECTS


class FakePoint:
    def __init__(self, x_value):
        self._x = x_value

    def x(self):
        return self._x


class FakeRect:
    def __init__(self, left=100):
        self._left = left

    def left(self):
        return self._left

    def center(self):
        return FakePoint(self._left + 100)


class FakeSurface:
    def __init__(self):
        self.hwnd = 11
        self.rect = FakeRect(100)

    def clamp_actor_x(self, x, actor_width):
        _ = actor_width
        return int(x)


class FakeTracker:
    def build_actor_snapshot(self, actor):
        return actor

    def can_actor_perch_on_surface(self, surface, actor):
        _ = surface
        _ = actor
        return True

    def get_surface_visible_center_x(self, surface, actor_width=0, preferred_center_x=None):
        _ = surface
        _ = actor_width
        return preferred_center_x


class FakeSurfaceSnapshot:
    left_bound = 0
    right_bound = 500
    floor_top_y = 400
    top_bound = 0

    def clamp_x(self, x):
        return int(x)


class FakeRng:
    def uniform(self, low, high):
        return (low + high) / 2.0

    def randint(self, low, high):
        return low


class FakePet:
    def __init__(self):
        self.window_tracker = FakeTracker()
        self.perched_window_hwnd = 0
        self.window_perch_offset_x = 0
        self.window_perch_mode = "idle"
        self.window_perch_origin = "manual"
        self.window_perch_end_time = 0.0
        self.vy = 0.0
        self.state = "idle"
        self.state_timer = 0
        self.direction = 1
        self.flight_mode = "none"
        self.flight_target_hwnd = 0
        self.flight_target_x = 0
        self.flight_target_y = 0
        self.flight_cooldown_end = 0.0
        self.moves = []
        self.animation_calls = []
        self.change_state_calls = []
        self.refresh_calls = 0
        self.reset_calls = 0

    def can_attach_to_window_surface(self):
        return True

    def geometry(self):
        return FakeRect(140)

    def width(self):
        return 80

    def x(self):
        return 150

    def y(self):
        return 220

    def get_window_perch_y(self, surface):
        _ = surface
        return 180

    def move(self, x, y):
        self.moves.append((x, y))

    def ensure_candidate_animation(self, candidates, context=None):
        self.animation_calls.append((tuple(candidates), context))
        return True

    def ensure_window_perch_animation(self):
        return self.ensure_candidate_animation(self.get_window_perch_candidates(), context="window_perch")

    def get_window_perch_candidates(self):
        return [("idle", "stand")]

    def refresh_movement_state(self):
        self.refresh_calls += 1

    def get_free_fly_candidates(self):
        return [("move", "fly")]

    def ensure_window_flight_animation(self):
        return self.ensure_candidate_animation(self.get_free_fly_candidates(), context="window_flight")

    def reset_stationary_move_mode(self):
        self.reset_calls += 1

    def get_surface_snapshot(self):
        return FakeSurfaceSnapshot()

    def get_taskbar_walk_y(self):
        return 390

    def can_fly_freely(self):
        return True

    def get_window_flight_speed(self):
        return 4.0

    def move_flight_toward(self, target_x, target_y, speed=None):
        _ = target_x
        _ = target_y
        _ = speed
        return True

    def change_state(self, purpose, action_type=None):
        self.change_state_calls.append((purpose, action_type))

class WindowingEffectsTests(unittest.TestCase):
    def test_attach_to_window_surface_sets_basic_perch_state(self):
        pet = FakePet()
        surface = FakeSurface()

        attached = WINDOWING_EFFECTS.attach_to_window_surface(
            pet,
            surface,
            origin="auto",
            preferred_center_x=180,
            now=100.0,
            rng=FakeRng(),
        )

        self.assertTrue(attached)
        self.assertEqual(pet.perched_window_hwnd, 11)
        self.assertEqual(pet.window_perch_origin, "auto")
        self.assertEqual(pet.window_perch_end_time, 109.0)
        self.assertEqual(pet.state, "idle")
        self.assertEqual(pet.state_timer, 80)
        self.assertEqual(pet.moves[-1], (140, 180))

    def test_apply_perch_detach_to_taskbar_sets_fall_when_flight_unavailable(self):
        pet = FakePet()
        pet.perched_window_hwnd = 11
        pet.can_fly_freely = lambda: False

        handled = WINDOWING_EFFECTS.apply_perch_detach_to_taskbar(pet, 220, now=20.0, rng=FakeRng())

        self.assertFalse(handled)
        self.assertEqual(pet.perched_window_hwnd, 0)
        self.assertEqual(pet.vy, 1.0)

    def test_apply_window_flight_attach_stops_and_attaches(self):
        pet = FakePet()
        pet.flight_mode = "to_window"
        surface = FakeSurface()

        attached = WINDOWING_EFFECTS.apply_window_flight_attach(
            pet,
            surface,
            anchor_center_x=170,
            now=50.0,
            rng=FakeRng(),
        )

        self.assertTrue(attached)
        self.assertEqual(pet.flight_mode, "none")
        self.assertEqual(pet.perched_window_hwnd, 11)


if __name__ == "__main__":
    unittest.main()
