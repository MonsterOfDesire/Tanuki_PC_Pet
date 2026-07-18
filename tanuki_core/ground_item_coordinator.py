from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from PyQt6.QtCore import QPoint
from PyQt6.QtWidgets import QApplication

from .offer_ground_item_ui import GroundOfferItemWidget
from .offer_interaction_rules import (
    GROUND_ITEM_FALL_GRAVITY,
    GROUND_ITEM_LIFETIME_SECONDS,
    GROUND_ITEM_MAX_FALL_SPEED,
    GROUND_ITEM_PICKUP_RADIUS,
    get_ground_pickup_pet_names,
    get_offer_item_definition,
)
from .runtime import app_now


def get_screen_for_global_position(global_x, global_y):
    point = QPoint(int(round(global_x)), int(round(global_y)))
    return QApplication.screenAt(point) or QApplication.primaryScreen()


@dataclass
class GroundOfferItem:
    item_kind: str
    widget: object
    x: float
    y: float
    floor_y: float
    vy: float = 0.0
    dropped_at: float = 0.0
    expires_at: float = 0.0


@dataclass
class GroundItemCoordinator:
    ground_items: list
    now_provider: Callable[[], float] = app_now
    screen_provider: Callable[[float, float], object | None] = get_screen_for_global_position

    def clear_ground_items(self) -> None:
        for dropped_item in self.ground_items:
            widget = getattr(dropped_item, "widget", None)
            if widget is None:
                continue
            widget.close()
            widget.deleteLater()
        self.ground_items.clear()

    @staticmethod
    def clear_held_item(pet, *, unlock_offer_scene) -> None:
        widget = getattr(pet, "held_item_widget", None)
        if widget is not None:
            widget.close()
            widget.deleteLater()
        pet.held_item_kind = ""
        pet.held_item_source = "none"
        pet.held_item_started_at = 0.0
        pet.held_item_widget = None
        if getattr(pet, "offer_scene_kind", "none") == "held_item":
            unlock_offer_scene(pet, expected_scene_kind="held_item")

    @staticmethod
    def build_widget(
        item_kind,
        *,
        draggable=False,
        drop_handler=None,
        hover_handler=None,
        clear_hover_handler=None,
    ):
        item_definition = get_offer_item_definition(item_kind)
        if item_definition is None:
            return None
        return GroundOfferItemWidget(
            item_kind=item_kind,
            icon_relative_path=item_definition.icon_relative_path,
            label=item_definition.label,
            draggable=draggable,
            drop_handler=drop_handler,
            hover_handler=hover_handler,
            clear_hover_handler=clear_hover_handler,
        )

    def ensure_held_item(
        self,
        pet,
        item_kind,
        *,
        source="offer_tray",
        clear_held_item,
        build_widget,
    ):
        if (
            getattr(pet, "held_item_kind", "") == item_kind
            and getattr(pet, "held_item_widget", None) is not None
        ):
            return pet.held_item_widget
        clear_held_item(pet)
        widget = build_widget(item_kind, draggable=False)
        if widget is None:
            return None
        pet.held_item_kind = item_kind
        pet.held_item_source = source
        pet.held_item_started_at = self.now_provider()
        pet.held_item_widget = widget
        return widget

    def find_by_widget(self, widget):
        for dropped_item in self.ground_items:
            if getattr(dropped_item, "widget", None) is widget:
                return dropped_item
        return None

    def drop_item(self, item_kind, global_pos, *, build_widget) -> bool:
        widget = build_widget(item_kind, draggable=True)
        if widget is None:
            return False
        global_x = float(global_pos.x())
        global_y = float(global_pos.y())
        screen = self.screen_provider(global_x, global_y)
        if screen is None:
            widget.deleteLater()
            return False
        available_rect = screen.availableGeometry()
        dropped_at = self.now_provider()
        dropped_item = GroundOfferItem(
            item_kind=item_kind,
            widget=widget,
            x=max(
                float(available_rect.left()),
                min(float(available_rect.right() - widget.width()), global_x - (widget.width() / 2.0)),
            ),
            y=max(
                float(available_rect.top()),
                min(float(available_rect.bottom() - widget.height()), global_y - (widget.height() / 2.0)),
            ),
            floor_y=float(available_rect.bottom() - widget.height()),
            vy=0.0,
            dropped_at=dropped_at,
            expires_at=dropped_at + GROUND_ITEM_LIFETIME_SECONDS,
        )
        self.ground_items.append(dropped_item)
        self.place_item(dropped_item, global_pos)
        return True

    def place_item(self, dropped_item, global_pos) -> bool:
        global_x = float(global_pos.x())
        global_y = float(global_pos.y())
        screen = self.screen_provider(global_x, global_y)
        if screen is None:
            return False
        available_rect = screen.availableGeometry()
        dropped_item.x = max(
            float(available_rect.left()),
            min(
                float(available_rect.right() - dropped_item.widget.width()),
                global_x - (dropped_item.widget.width() / 2.0),
            ),
        )
        dropped_item.y = max(
            float(available_rect.top()),
            min(
                float(available_rect.bottom() - dropped_item.widget.height()),
                global_y - (dropped_item.widget.height() / 2.0),
            ),
        )
        dropped_item.floor_y = float(available_rect.bottom() - dropped_item.widget.height())
        dropped_item.vy = 0.0
        dropped_item.dropped_at = self.now_provider()
        dropped_item.expires_at = float(dropped_item.dropped_at) + GROUND_ITEM_LIFETIME_SECONDS
        dropped_item.widget.move_to(dropped_item.x, dropped_item.y)
        dropped_item.widget.show()
        dropped_item.widget.raise_()
        return True

    def remove_item(self, dropped_item) -> None:
        widget = getattr(dropped_item, "widget", None)
        if widget is not None:
            widget.close()
            widget.deleteLater()
        if dropped_item in self.ground_items:
            self.ground_items.remove(dropped_item)

    def update_items(self, now, *, offer_scene_active, try_pickup) -> bool:
        if not self.ground_items:
            return False
        handled = False
        for dropped_item in list(self.ground_items):
            if now >= float(dropped_item.expires_at):
                self.remove_item(dropped_item)
                handled = True
                continue
            if dropped_item.y < dropped_item.floor_y:
                dropped_item.vy = min(
                    float(dropped_item.vy) + GROUND_ITEM_FALL_GRAVITY,
                    GROUND_ITEM_MAX_FALL_SPEED,
                )
                dropped_item.y = min(
                    float(dropped_item.floor_y),
                    float(dropped_item.y) + float(dropped_item.vy),
                )
                dropped_item.widget.move_to(dropped_item.x, dropped_item.y)
            if offer_scene_active() or dropped_item.y < (dropped_item.floor_y - 1.0):
                continue
            if try_pickup(dropped_item):
                handled = True
        return handled

    def try_pickup_item(
        self,
        dropped_item,
        *,
        find_pet_by_name,
        pet_is_busy,
        start_interaction,
    ) -> bool:
        item_center_x = float(dropped_item.x) + (dropped_item.widget.width() / 2.0)
        pickup_candidates = []
        for pet_name in get_ground_pickup_pet_names(dropped_item.item_kind):
            pet = find_pet_by_name(pet_name, visible_only=True)
            if (
                pet is None
                or pet.dragging
                or pet.is_offer_locked(self.now_provider())
                or pet_is_busy(pet)
            ):
                continue
            surface = pet.get_surface_snapshot()
            if pet.y() < (surface.floor_top_y - 12):
                continue
            pet_center_x = pet.x() + (pet.width() / 2.0)
            distance = abs(float(pet_center_x) - item_center_x)
            if distance > GROUND_ITEM_PICKUP_RADIUS:
                continue
            pickup_candidates.append((distance, pet))
        if not pickup_candidates:
            return False
        pickup_candidates.sort(key=lambda item: item[0])
        target_pet = pickup_candidates[0][1]
        target_center_x = target_pet.x() + (target_pet.width() / 2.0)
        target_pet.direction = -1 if item_center_x < target_center_x else 1
        self.remove_item(dropped_item)
        return start_interaction(
            dropped_item.item_kind,
            target_pet,
            source="ground_pickup",
        )
