import os
import types
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QRect

from tanuki_core.display_topology import (
    pet_is_safe_for_floor_reconcile,
    reconcile_pet_floor_position,
    select_leftmost_screen,
)
from tanuki_core.geometry import DesktopGeometry


class FakeScreen:
    def __init__(self, geometry, available=None):
        self._geometry = QRect(geometry)
        self._available = QRect(available or geometry)

    def geometry(self):
        return QRect(self._geometry)

    def availableGeometry(self):
        return QRect(self._available)


class FakePet:
    def __init__(self, geometry):
        self._geometry = QRect(geometry)
        self.dragging = False
        self.drag_press_pending = False
        self.throw_active = False
        self.vy = 0.0
        self.flight_mode = "none"
        self.perched_window_hwnd = 0
        self.care_mode = "none"
        self.transformation_state = types.SimpleNamespace(active=False)
        self.activity_locked = False
        self.offer_locked = False
        self.refresh_calls = 0

    def geometry(self):
        return QRect(self._geometry)

    def width(self):
        return self._geometry.width()

    def height(self):
        return self._geometry.height()

    def x(self):
        return self._geometry.x()

    def y(self):
        return self._geometry.y()

    def move(self, x, y):
        self._geometry.moveTo(int(x), int(y))

    def is_activity_locked(self):
        return self.activity_locked

    def is_offer_locked(self):
        return self.offer_locked

    def refresh_movement_state(self):
        self.refresh_calls += 1


class DisplayTopologyTests(unittest.TestCase):
    def setUp(self):
        self.left = FakeScreen(QRect(-1920, 0, 1920, 1080))
        self.main = FakeScreen(
            QRect(0, 0, 2560, 1664),
            QRect(0, 0, 2560, 1600),
        )

    def test_leftmost_screen_is_reselected_from_current_topology(self):
        self.assertIs(select_leftmost_screen([self.main, self.left]), self.left)
        self.assertIs(select_leftmost_screen([self.main]), self.main)

    def test_screen_selection_prefers_largest_actor_intersection(self):
        actor = QRect(-200, 400, 300, 300)

        selected = DesktopGeometry.get_screen_for_rect(
            actor,
            screens=[self.main, self.left],
        )

        self.assertIs(selected, self.left)

    def test_floor_reconcile_clamps_to_selected_screen_and_available_floor(self):
        pet = FakePet(QRect(-2100, 120, 240, 240))

        moved = reconcile_pet_floor_position(
            pet,
            [self.main, self.left],
        )

        self.assertTrue(moved)
        self.assertEqual(pet.x(), -1920)
        self.assertEqual(pet.y(), 839)
        self.assertEqual(pet.refresh_calls, 1)

    def test_busy_pet_is_deferred_instead_of_teleported(self):
        pet = FakePet(QRect(-2100, 120, 240, 240))
        pet.activity_locked = True

        self.assertFalse(pet_is_safe_for_floor_reconcile(pet))
        self.assertFalse(
            reconcile_pet_floor_position(pet, [self.main, self.left])
        )
        self.assertEqual(pet.geometry(), QRect(-2100, 120, 240, 240))

    def test_thrown_pet_is_not_reconciled_mid_flight(self):
        pet = FakePet(QRect(-2100, 120, 240, 240))
        pet.throw_active = True

        self.assertFalse(pet_is_safe_for_floor_reconcile(pet))
        self.assertFalse(
            reconcile_pet_floor_position(pet, [self.main, self.left])
        )


if __name__ == "__main__":
    unittest.main()
