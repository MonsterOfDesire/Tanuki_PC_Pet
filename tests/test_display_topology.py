import os
import types
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPoint, QRect

from tanuki_core.display_topology import (
    pet_is_safe_for_floor_reconcile,
    reconcile_pet_floor_position,
    select_leftmost_screen,
)
from tanuki_core.geometry import DesktopGeometry
from tanuki_core.pet_widget import TanukiPet


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


class FakeDraggedPet(FakePet):
    def __init__(self, geometry):
        super().__init__(geometry)
        self.dragging = True
        self.drag_pos = QPoint(self.width() // 2, self.height() // 2)
        self.drag_motion_samples = ()
        self.drag_target_x = float(self.x())
        self.drag_target_y = float(self.y())
        self.drag_target_screen_rect = None
        self.drag_follow_x = float(self.x())
        self.drag_follow_y = float(self.y())
        self.drag_follow_velocity_x = 0.0
        self.drag_follow_velocity_y = 0.0
        self.drag_follow_last_at = 1.0
        self.drag_follow_active = True


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

    def test_stacked_offset_monitor_does_not_create_walkable_virtual_gap(self):
        upper_left = FakeScreen(QRect(-1920, -1080, 1920, 1080))
        actor = QRect(100, 1300, 240, 240)

        left_bound, right_bound = DesktopGeometry.get_horizontal_movement_bounds(
            actor,
            screens=[self.main, upper_left],
            selected_screen=self.main,
        )

        self.assertEqual(left_bound, 0)
        self.assertEqual(right_bound, 2319)

    def test_aligned_side_by_side_monitors_share_walkable_corridor(self):
        actor = QRect(100, 700, 240, 240)

        left_bound, right_bound = DesktopGeometry.get_horizontal_movement_bounds(
            actor,
            screens=[self.main, self.left],
            selected_screen=self.main,
        )

        self.assertEqual(left_bound, -1920)
        self.assertEqual(right_bound, 2319)

    def test_drag_position_uses_target_monitor_instead_of_current_monitor(self):
        pet = FakePet(QRect(100, 1300, 240, 240))
        upper_left = FakeScreen(QRect(-1920, -1080, 1920, 1080))

        with patch(
            "tanuki_core.geometry.QApplication.screens",
            return_value=[self.main, upper_left],
        ):
            x, y = DesktopGeometry.clamp_drag_position(
                pet,
                -1500,
                -800,
            )

        self.assertEqual((x, y), (-1500, -800))

    def _drag_frames(self, start, target, screens):
        pet = FakeDraggedPet(QRect(*start, 240, 240))
        cursor = QPoint(*target) + pet.drag_pos
        event = types.SimpleNamespace(
            globalPosition=lambda: types.SimpleNamespace(toPoint=lambda: cursor),
        )
        positions = [start]
        with patch(
            "tanuki_core.geometry.QApplication.screens",
            return_value=screens,
        ):
            TanukiPet.mouseMoveEvent(pet, event)
            for frame in range(1, 121):
                TanukiPet._advance_drag_follow(pet, now=1.0 + frame * 0.016)
                positions.append((pet.x(), pet.y()))
        return pet, positions

    def test_smooth_drag_crosses_side_by_side_seam_in_both_directions(self):
        for start, target in (
            ((1000, 500), (-900, 500)),
            ((-900, 500), (1000, 500)),
        ):
            with self.subTest(start=start):
                pet, positions = self._drag_frames(
                    start, target, [self.main, self.left],
                )
                self.assertLessEqual(abs(pet.x() - target[0]), 1)
                self.assertEqual(pet.y(), target[1])
                self.assertLessEqual(
                    max(abs(b[0] - a[0]) for a, b in zip(positions, positions[1:])),
                    42,
                )

    def test_smooth_drag_crosses_vertical_seam_in_both_directions(self):
        upper = FakeScreen(QRect(0, -1080, 2560, 1080))
        for start, target in (
            ((800, 700), (800, -700)),
            ((800, -700), (800, 700)),
        ):
            with self.subTest(start=start):
                pet, positions = self._drag_frames(start, target, [self.main, upper])
                self.assertEqual(pet.x(), target[0])
                self.assertLessEqual(abs(pet.y() - target[1]), 1)
                self.assertLessEqual(
                    max(abs(b[1] - a[1]) for a, b in zip(positions, positions[1:])),
                    42,
                )

    def test_smooth_drag_hands_off_once_across_offset_monitor_gap(self):
        upper_left = FakeScreen(QRect(-1920, -1300, 1920, 1080))
        for start, target in (
            ((1000, 700), (-900, -800)),
            ((-900, -800), (1000, 700)),
        ):
            with self.subTest(start=start):
                pet, positions = self._drag_frames(
                    start, target, [self.main, upper_left],
                )
                self.assertLessEqual(abs(pet.x() - target[0]), 1)
                self.assertLessEqual(abs(pet.y() - target[1]), 1)
                handoffs = [
                    (a, b) for a, b in zip(positions, positions[1:])
                    if max(abs(b[0] - a[0]), abs(b[1] - a[1])) > 42
                ]
                self.assertEqual(len(handoffs), 1)
                for x, y in positions:
                    self.assertTrue(any(
                        screen.geometry().contains(QRect(x, y, 240, 240))
                        for screen in (self.main, upper_left)
                    ))

    def test_cursor_in_gap_keeps_previous_drag_target_screen(self):
        upper_left = FakeScreen(QRect(-1920, -1300, 1920, 1080))
        previous = self.main.geometry()
        with patch(
            "tanuki_core.geometry.QApplication.screens",
            return_value=[self.main, upper_left],
        ):
            selected = DesktopGeometry.get_drag_target_screen_rect(
                -100, -100, previous_screen_rect=previous,
            )
        self.assertEqual(selected, previous)
        self.assertIsNot(selected, previous)

    def test_cursor_crossing_seam_changes_target_before_actor_majority_crosses(self):
        pet = FakeDraggedPet(QRect(-300, 500, 240, 240))
        pet.drag_target_screen_rect = self.left.geometry()
        cursor = QPoint(5, 620)
        event = types.SimpleNamespace(
            globalPosition=lambda: types.SimpleNamespace(toPoint=lambda: cursor),
        )
        with patch(
            "tanuki_core.geometry.QApplication.screens",
            return_value=[self.main, self.left],
        ):
            TanukiPet.mouseMoveEvent(pet, event)
        self.assertEqual(pet.drag_target_screen_rect, self.main.geometry())
        self.assertEqual(pet.drag_target_x, 0.0)
        self.assertEqual(pet.x(), -300)

    def test_removed_drag_target_monitor_falls_back_to_current_topology(self):
        pet = FakeDraggedPet(QRect(-300, 500, 240, 240))
        pet.drag_target_screen_rect = self.left.geometry()
        with patch(
            "tanuki_core.geometry.QApplication.screens",
            return_value=[self.main],
        ):
            x, y = DesktopGeometry.clamp_drag_follow_position(
                pet, -350, 500, target_screen_rect=pet.drag_target_screen_rect,
            )
            selected = DesktopGeometry.get_drag_target_screen_rect(
                -300, 500, previous_screen_rect=pet.drag_target_screen_rect,
            )
        self.assertEqual((x, y), (0, 500))
        self.assertIsNone(selected)

    def test_same_screen_drag_retains_existing_partial_top_visibility(self):
        pet = FakeDraggedPet(QRect(300, 0, 240, 240))
        with patch(
            "tanuki_core.geometry.QApplication.screens",
            return_value=[self.main],
        ):
            x, y = DesktopGeometry.clamp_drag_follow_position(
                pet, 300, -300, target_screen_rect=self.main.geometry(),
            )
        self.assertEqual((x, y), (300, -156))

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
