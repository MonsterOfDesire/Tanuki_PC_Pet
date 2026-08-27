from __future__ import annotations

from PyQt6.QtCore import QObject, QTimer

from .geometry import DesktopGeometry
from .transformation_profiles import pet_is_transforming


TOPOLOGY_DEBOUNCE_MS = 160
PENDING_RETRY_MS = 250
FLOOR_GUARD_INTERVAL_MS = 1000
FLOOR_TOLERANCE_PX = 3


def select_leftmost_screen(screens):
    candidates = tuple(screens or ())
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda screen: (
            screen.geometry().left(),
            screen.geometry().top(),
            screen.geometry().width(),
            screen.geometry().height(),
        ),
    )


def pet_is_safe_for_floor_reconcile(pet):
    if bool(getattr(pet, "dragging", False)):
        return False
    if bool(getattr(pet, "drag_press_pending", False)):
        return False
    if float(getattr(pet, "vy", 0.0) or 0.0) != 0.0:
        return False
    if str(getattr(pet, "flight_mode", "none") or "none") != "none":
        return False
    if bool(getattr(pet, "perched_window_hwnd", None)):
        return False
    if str(getattr(pet, "care_mode", "none") or "none") != "none":
        return False
    if pet_is_transforming(pet):
        return False
    activity_locked = getattr(pet, "is_activity_locked", None)
    if callable(activity_locked) and activity_locked():
        return False
    offer_locked = getattr(pet, "is_offer_locked", None)
    if callable(offer_locked) and offer_locked():
        return False
    return True


def reconcile_pet_floor_position(
    pet,
    screens,
    *,
    tolerance_px=FLOOR_TOLERANCE_PX,
):
    candidates = tuple(screens or ())
    if not candidates or not pet_is_safe_for_floor_reconcile(pet):
        return False

    screen = DesktopGeometry.get_screen_for_rect(
        pet.geometry(),
        screens=candidates,
    )
    if screen is None:
        return False
    screen_rect = screen.geometry()
    available_rect = screen.availableGeometry()
    maximum_x = screen_rect.right() - int(pet.width()) + 1
    target_x = max(
        screen_rect.left(),
        min(int(pet.x()), maximum_x),
    )
    target_y = available_rect.bottom() - int(pet.height())
    needs_move = (
        target_x != int(pet.x())
        or abs(target_y - int(pet.y())) > max(0, int(tolerance_px))
    )
    if needs_move:
        pet.move(target_x, target_y)
    refresh_movement_state = getattr(pet, "refresh_movement_state", None)
    if callable(refresh_movement_state):
        refresh_movement_state()
    return needs_move


class DisplayTopologyCoordinator(QObject):
    def __init__(
        self,
        *,
        app,
        dashboard,
        pets,
        sensor=None,
        capabilities=None,
        screen_provider=None,
    ):
        super().__init__(app)
        self.app = app
        self.dashboard = dashboard
        self.pets = tuple(pets or ())
        self.sensor = sensor
        self.capabilities = capabilities
        self.screen_provider = screen_provider or (
            lambda: tuple(self.app.screens())
        )
        self._bound_screens = {}
        self._pending_pets = {}
        self._started = False

        self._topology_timer = QTimer(self)
        self._topology_timer.setSingleShot(True)
        self._topology_timer.timeout.connect(self.reconcile_now)
        self._pending_timer = QTimer(self)
        self._pending_timer.setSingleShot(True)
        self._pending_timer.timeout.connect(self._retry_pending_pets)
        self._floor_guard_timer = QTimer(self)
        self._floor_guard_timer.timeout.connect(self._guard_floor_anchors)

    def start(self):
        if self._started:
            return
        self._started = True
        self.app.screenAdded.connect(self._handle_screen_added)
        self.app.screenRemoved.connect(self._handle_screen_removed)
        primary_changed = getattr(self.app, "primaryScreenChanged", None)
        if primary_changed is not None:
            primary_changed.connect(self.schedule_reconcile)
        for screen in self.screen_provider():
            self._bind_screen(screen)
        floor_guard_enabled = bool(
            self.capabilities
            and self.capabilities.floor_anchor_guard
        )
        if floor_guard_enabled:
            self._floor_guard_timer.start(FLOOR_GUARD_INTERVAL_MS)
            self.reconcile_now()

    def shutdown(self):
        if not self._started:
            return
        self._started = False
        self._topology_timer.stop()
        self._pending_timer.stop()
        self._floor_guard_timer.stop()
        for signal, slot in (
            (self.app.screenAdded, self._handle_screen_added),
            (self.app.screenRemoved, self._handle_screen_removed),
            (
                getattr(self.app, "primaryScreenChanged", None),
                self.schedule_reconcile,
            ),
        ):
            if signal is None:
                continue
            try:
                signal.disconnect(slot)
            except (RuntimeError, TypeError):
                pass
        for screen in tuple(self._bound_screens.values()):
            self._unbind_screen(screen)
        self._pending_pets.clear()

    def _bind_screen(self, screen):
        key = id(screen)
        if key in self._bound_screens:
            return
        self._bound_screens[key] = screen
        for signal_name in (
            "geometryChanged",
            "availableGeometryChanged",
            "logicalDotsPerInchChanged",
        ):
            signal = getattr(screen, signal_name, None)
            if signal is not None:
                signal.connect(self.schedule_reconcile)

    def _unbind_screen(self, screen):
        self._bound_screens.pop(id(screen), None)
        for signal_name in (
            "geometryChanged",
            "availableGeometryChanged",
            "logicalDotsPerInchChanged",
        ):
            try:
                signal = getattr(screen, signal_name, None)
            except RuntimeError:
                continue
            if signal is None:
                continue
            try:
                signal.disconnect(self.schedule_reconcile)
            except (RuntimeError, TypeError):
                pass

    def _handle_screen_added(self, screen):
        self._bind_screen(screen)
        self.schedule_reconcile()

    def _handle_screen_removed(self, screen):
        self._unbind_screen(screen)
        self.schedule_reconcile()

    def schedule_reconcile(self, *_args):
        if not self._started:
            return
        self._topology_timer.start(TOPOLOGY_DEBOUNCE_MS)

    def reconcile_now(self):
        screens = tuple(self.screen_provider())
        target_screen = select_leftmost_screen(screens)
        if target_screen is None:
            return False
        target_rect = target_screen.availableGeometry()
        self.dashboard.reconcile_screen_geometry(target_rect)
        if self.sensor is not None:
            sensor_height = min(300, max(1, target_rect.height()))
            self.sensor.setGeometry(
                target_rect.left(),
                target_rect.bottom() - sensor_height,
                20,
                sensor_height,
            )

        self._pending_pets.clear()
        for pet in self.pets:
            if not pet_is_safe_for_floor_reconcile(pet):
                self._pending_pets[id(pet)] = pet
                continue
            reconcile_pet_floor_position(pet, screens)
        if self._pending_pets:
            self._pending_timer.start(PENDING_RETRY_MS)
        return True

    def _retry_pending_pets(self):
        if not self._pending_pets:
            return
        screens = tuple(self.screen_provider())
        remaining = {}
        for pet in tuple(self._pending_pets.values()):
            if not pet_is_safe_for_floor_reconcile(pet):
                remaining[id(pet)] = pet
                continue
            reconcile_pet_floor_position(pet, screens)
        self._pending_pets = remaining
        if remaining:
            self._pending_timer.start(PENDING_RETRY_MS)

    def _guard_floor_anchors(self):
        screens = tuple(self.screen_provider())
        for pet in self.pets:
            reconcile_pet_floor_position(pet, screens)
