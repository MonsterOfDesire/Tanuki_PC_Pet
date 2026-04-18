import unittest

from tanuki_core.pet_windowing import PetWindowingMixin
from tanuki_core.windowing_coordinator import (
    WINDOWING_COORDINATOR,
    WINDOW_FLIGHT_DECISION_ATTACH,
    WINDOW_FLIGHT_DECISION_NONE,
    WINDOW_FLIGHT_DECISION_STOP,
    WINDOW_FLIGHT_DECISION_TASKBAR_TICK,
    WINDOW_FLIGHT_DECISION_WINDOW_TICK,
    WINDOW_PERCH_DECISION_CONTINUE,
    WINDOW_PERCH_DECISION_DETACH,
    WINDOW_PERCH_DECISION_DETACH_TO_TASKBAR,
    WindowFlightContext,
    WindowPerchContext,
)


class WindowPerchCoordinatorTests(unittest.TestCase):
    def test_update_window_perch_returns_false_when_pet_is_not_perched(self):
        class DummyPet:
            perched_window_hwnd = 0
            window_tracker = None
            dragging = False
            care_mode = "none"
            social_mode = "none"
            is_recovering = False
            is_adult = False
            window_perch_origin = "manual"
            window_perch_end_time = 0.0

            def x(self):
                return 100

            def is_distressed(self):
                return False

        self.assertFalse(PetWindowingMixin.update_window_perch(DummyPet()))

    def test_window_perch_detaches_when_runtime_state_blocks_perching(self):
        decision = WINDOWING_COORDINATOR.decide_window_perch(WindowPerchContext(
            is_perched=True,
            dragging=True,
            care_mode="none",
            social_mode="none",
            is_recovering=False,
            has_window_tracker=True,
            has_surface=True,
            can_perch_on_surface=True,
            is_child_distressed=False,
            adult_should_leave_for_care=False,
            auto_perch_expired=False,
            current_x=120,
        ))

        self.assertEqual(decision.action, WINDOW_PERCH_DECISION_DETACH)

    def test_window_perch_detaches_to_taskbar_for_distress_and_expiry(self):
        child = WINDOWING_COORDINATOR.decide_window_perch(WindowPerchContext(
            is_perched=True,
            dragging=False,
            care_mode="none",
            social_mode="none",
            is_recovering=False,
            has_window_tracker=True,
            has_surface=True,
            can_perch_on_surface=True,
            is_child_distressed=True,
            adult_should_leave_for_care=False,
            auto_perch_expired=False,
            current_x=140,
        ))
        auto = WINDOWING_COORDINATOR.decide_window_perch(WindowPerchContext(
            is_perched=True,
            dragging=False,
            care_mode="none",
            social_mode="none",
            is_recovering=False,
            has_window_tracker=True,
            has_surface=True,
            can_perch_on_surface=True,
            is_child_distressed=False,
            adult_should_leave_for_care=False,
            auto_perch_expired=True,
            current_x=140,
            fallback_target_x=300,
        ))

        self.assertEqual(child.action, WINDOW_PERCH_DECISION_DETACH_TO_TASKBAR)
        self.assertEqual(child.target_x, 140)
        self.assertEqual(auto.action, WINDOW_PERCH_DECISION_DETACH_TO_TASKBAR)
        self.assertEqual(auto.target_x, 300)

    def test_window_perch_continues_when_surface_is_valid(self):
        decision = WINDOWING_COORDINATOR.decide_window_perch(WindowPerchContext(
            is_perched=True,
            dragging=False,
            care_mode="none",
            social_mode="none",
            is_recovering=False,
            has_window_tracker=True,
            has_surface=True,
            can_perch_on_surface=True,
            is_child_distressed=False,
            adult_should_leave_for_care=False,
            auto_perch_expired=False,
            current_x=200,
        ))

        self.assertEqual(decision.action, WINDOW_PERCH_DECISION_CONTINUE)
        self.assertTrue(decision.handled)

    def test_update_window_perch_detaches_when_current_perch_position_is_occluded(self):
        class DummyPoint:
            def __init__(self, x_value):
                self._x = x_value

            def x(self):
                return self._x

        class DummyRect:
            def __init__(self, center_x):
                self._center = DummyPoint(center_x)

            def center(self):
                return self._center

        class DummySurfaceRect:
            def __init__(self):
                self._left = 0
                self._top = 100
                self._width = 300

            def left(self):
                return self._left

            def top(self):
                return self._top

            def width(self):
                return self._width

            def center(self):
                return DummyPoint(150)

        class DummySurface:
            hwnd = 1
            rect = DummySurfaceRect()

        class DummyTracker:
            def __init__(self):
                self.surface = DummySurface()

            def get_surface_by_hwnd(self, hwnd):
                return self.surface if hwnd == 1 else None

            def build_actor_snapshot(self, actor):
                return actor

            def can_actor_perch_on_surface(self, surface, actor):
                return True

            def is_actor_perch_position_visible(self, surface, actor, preferred_center_x=None):
                return False

        class DummyPet(PetWindowingMixin):
            def __init__(self):
                self.perched_window_hwnd = 1
                self.window_tracker = DummyTracker()
                self.dragging = False
                self.care_mode = "none"
                self.social_mode = "none"
                self.is_recovering = False
                self.is_adult = False
                self.window_perch_origin = "manual"
                self.window_perch_end_time = 0.0
                self.flight_mode = "none"
                self.flight_target_hwnd = 0
                self.flight_target_x = 0
                self.flight_target_y = 0
                self.vy = 0.0
                self.state = "idle"
                self.direction = 1

            def geometry(self):
                return DummyRect(180)

            def x(self):
                return 140

            def width(self):
                return 80

            def is_distressed(self):
                return False

            def refresh_movement_state(self):
                pass

            def can_fly_freely(self):
                return True

            def get_surface_snapshot(self):
                class Surface:
                    def clamp_x(self_inner, value):
                        return value

                return Surface()

            def get_taskbar_walk_y(self):
                return 300

            def reset_stationary_move_mode(self):
                pass

            def ensure_candidate_animation(self, candidates, context=None):
                return True

            def get_free_fly_candidates(self):
                return [("move", "fly")]

        pet = DummyPet()

        handled = pet.update_window_perch()

        self.assertFalse(handled)
        self.assertEqual(pet.perched_window_hwnd, 0)
        self.assertEqual(pet.flight_mode, "to_taskbar")
        self.assertEqual(pet.flight_target_x, 140)
        self.assertEqual(pet.flight_target_y, 300)


class WindowFlightCoordinatorTests(unittest.TestCase):
    def test_window_flight_stops_when_runtime_state_is_invalid(self):
        decision = WINDOWING_COORDINATOR.decide_window_flight(WindowFlightContext(
            mode="to_window",
            dragging=True,
            care_mode="none",
            social_mode="none",
            is_recovering=False,
            has_window_tracker=True,
            has_surface=True,
            can_perch_on_surface=True,
            has_anchor_center=True,
            distance_to_target=40.0,
        ))

        self.assertEqual(decision.action, WINDOW_FLIGHT_DECISION_STOP)

    def test_window_flight_handles_taskbar_tick_and_attach(self):
        taskbar = WINDOWING_COORDINATOR.decide_window_flight(WindowFlightContext(
            mode="to_taskbar",
            dragging=False,
            care_mode="none",
            social_mode="none",
            is_recovering=False,
            has_window_tracker=True,
            has_surface=False,
            can_perch_on_surface=False,
            has_anchor_center=False,
            distance_to_target=None,
        ))
        attach = WINDOWING_COORDINATOR.decide_window_flight(WindowFlightContext(
            mode="to_window",
            dragging=False,
            care_mode="none",
            social_mode="none",
            is_recovering=False,
            has_window_tracker=True,
            has_surface=True,
            can_perch_on_surface=True,
            has_anchor_center=True,
            distance_to_target=10.0,
        ))

        self.assertEqual(taskbar.action, WINDOW_FLIGHT_DECISION_TASKBAR_TICK)
        self.assertEqual(attach.action, WINDOW_FLIGHT_DECISION_ATTACH)

    def test_window_flight_continues_window_tick_when_target_is_far_enough(self):
        decision = WINDOWING_COORDINATOR.decide_window_flight(WindowFlightContext(
            mode="to_window",
            dragging=False,
            care_mode="none",
            social_mode="none",
            is_recovering=False,
            has_window_tracker=True,
            has_surface=True,
            can_perch_on_surface=True,
            has_anchor_center=True,
            distance_to_target=80.0,
        ))

        self.assertEqual(decision.action, WINDOW_FLIGHT_DECISION_WINDOW_TICK)
        self.assertTrue(decision.handled)

    def test_window_flight_returns_none_when_inactive(self):
        decision = WINDOWING_COORDINATOR.decide_window_flight(WindowFlightContext(
            mode="none",
            dragging=False,
            care_mode="none",
            social_mode="none",
            is_recovering=False,
            has_window_tracker=True,
            has_surface=False,
            can_perch_on_surface=False,
            has_anchor_center=False,
            distance_to_target=None,
        ))

        self.assertEqual(decision.action, WINDOW_FLIGHT_DECISION_NONE)

if __name__ == "__main__":
    unittest.main()
