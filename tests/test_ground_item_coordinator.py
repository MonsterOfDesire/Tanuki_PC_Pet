import unittest
from types import SimpleNamespace

from tanuki_core.ground_item_coordinator import (
    GroundItemCoordinator,
    GroundOfferItem,
)


class FakeWidget:
    def __init__(self, width=48, height=48):
        self._width = width
        self._height = height
        self.moves = []
        self.shown = 0
        self.raised = 0
        self.closed = 0
        self.deleted = 0

    def width(self):
        return self._width

    def height(self):
        return self._height

    def move_to(self, x, y):
        self.moves.append((x, y))

    def show(self):
        self.shown += 1

    def raise_(self):
        self.raised += 1

    def close(self):
        self.closed += 1

    def deleteLater(self):
        self.deleted += 1


class FakeRect:
    def left(self):
        return 0

    def top(self):
        return 0

    def right(self):
        return 999

    def bottom(self):
        return 799


class FakeScreen:
    def availableGeometry(self):
        return FakeRect()


class FakePet:
    def __init__(self, name, x=100):
        self.name = name
        self._x = x
        self.dragging = False
        self.direction = 1
        self.held_item_kind = ""
        self.held_item_source = "none"
        self.held_item_started_at = 0.0
        self.held_item_widget = None
        self.offer_scene_kind = "none"

    def x(self):
        return self._x

    def y(self):
        return 560

    def width(self):
        return 200

    def is_offer_locked(self, now):
        _ = now
        return False

    def get_surface_snapshot(self):
        return SimpleNamespace(floor_top_y=560)


class GroundItemCoordinatorTests(unittest.TestCase):
    def build_coordinator(self, items=None):
        return GroundItemCoordinator(
            ground_items=[] if items is None else items,
            now_provider=lambda: 10.0,
            screen_provider=lambda _x, _y: FakeScreen(),
        )

    def test_clear_ground_items_disposes_widgets_without_replacing_shared_list(self):
        widget = FakeWidget()
        items = [GroundOfferItem("tea", widget, 0, 0, 100)]
        coordinator = self.build_coordinator(items)

        coordinator.clear_ground_items()

        self.assertEqual(items, [])
        self.assertIs(coordinator.ground_items, items)
        self.assertEqual((widget.closed, widget.deleted), (1, 1))

    def test_ensure_held_item_sets_pet_state_and_reuses_existing_widget(self):
        coordinator = self.build_coordinator()
        pet = FakePet("Symboli Rudolf")
        widget = FakeWidget()
        build_calls = []

        first = coordinator.ensure_held_item(
            pet,
            "tea",
            source="offer_tray",
            clear_held_item=lambda target: coordinator.clear_held_item(
                target,
                unlock_offer_scene=lambda *_args, **_kwargs: None,
            ),
            build_widget=lambda item_kind, draggable=False: (
                build_calls.append((item_kind, draggable)) or widget
            ),
        )
        second = coordinator.ensure_held_item(
            pet,
            "tea",
            clear_held_item=lambda _target: None,
            build_widget=lambda *_args, **_kwargs: None,
        )

        self.assertIs(first, widget)
        self.assertIs(second, widget)
        self.assertEqual(build_calls, [("tea", False)])
        self.assertEqual(pet.held_item_kind, "tea")
        self.assertEqual(pet.held_item_started_at, 10.0)

    def test_drop_item_places_widget_and_tracks_shared_ground_item(self):
        coordinator = self.build_coordinator()
        widget = FakeWidget()
        global_pos = SimpleNamespace(x=lambda: 300, y=lambda: 200)

        dropped = coordinator.drop_item(
            "ramen",
            global_pos,
            build_widget=lambda _kind, draggable=False: widget if draggable else None,
        )

        self.assertTrue(dropped)
        self.assertEqual(len(coordinator.ground_items), 1)
        self.assertEqual(widget.moves[-1], (276.0, 176.0))
        self.assertEqual(coordinator.ground_items[0].expires_at, 70.0)

    def test_update_items_applies_gravity_and_removes_expired_item(self):
        falling_widget = FakeWidget()
        expired_widget = FakeWidget()
        falling = GroundOfferItem("tea", falling_widget, 10, 20, 100, expires_at=50)
        expired = GroundOfferItem("honey", expired_widget, 10, 100, 100, expires_at=5)
        coordinator = self.build_coordinator([falling, expired])

        handled = coordinator.update_items(
            10.0,
            offer_scene_active=lambda: False,
            try_pickup=lambda _item: False,
        )

        self.assertTrue(handled)
        self.assertAlmostEqual(falling.vy, 1.4)
        self.assertAlmostEqual(falling.y, 21.4)
        self.assertNotIn(expired, coordinator.ground_items)

    def test_try_pickup_item_chooses_nearest_eligible_pet_and_routes_source(self):
        widget = FakeWidget()
        dropped = GroundOfferItem("tea", widget, 190, 100, 100)
        coordinator = self.build_coordinator([dropped])
        near_pet = FakePet("Air Groove", x=120)
        far_pet = FakePet("Symboli Rudolf", x=20)
        pets = {near_pet.name: near_pet, far_pet.name: far_pet}
        starts = []

        picked_up = coordinator.try_pickup_item(
            dropped,
            find_pet_by_name=lambda name, visible_only=False: pets.get(name),
            pet_is_busy=lambda _pet: False,
            start_interaction=lambda item_kind, pet, source: (
                starts.append((item_kind, pet.name, source)) or True
            ),
        )

        self.assertTrue(picked_up)
        self.assertEqual(starts, [("tea", "Air Groove", "ground_pickup")])
        self.assertEqual(coordinator.ground_items, [])


if __name__ == "__main__":
    unittest.main()
