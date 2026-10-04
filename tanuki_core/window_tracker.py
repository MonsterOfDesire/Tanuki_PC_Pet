from PyQt6.QtCore import QObject, QPoint, QRect
from PyQt6.QtWidgets import QApplication

from .window_tracker_backend import create_window_tracker_backend
from .window_tracker_policy import WindowSurface, build_window_surface
from .window_surface_rules import (
    can_actor_perch_on_surface,
    get_surface_visible_center_x as choose_surface_visible_center_x,
    is_surface_perch_allowed as rule_is_surface_perch_allowed,
    is_surface_top_segment_visible as rule_is_surface_top_segment_visible,
)
from .window_surface_selector import (
    WindowActorSnapshot,
    find_drop_surface as select_drop_surface,
    find_flight_surface as select_flight_surface,
)

class WindowTracker(QObject):
    MIN_WINDOW_WIDTH = 180
    MIN_WINDOW_HEIGHT = 80
    SNAP_TOP_TOLERANCE = 110
    SNAP_DEPTH_LIMIT = 70
    TOP_EDGE_INSET = 18
    TOP_EDGE_Y_OFFSETS = (8, 18, 28)
    WS_EX_TOOLWINDOW = 0x00000080
    WS_CHILD = 0x40000000
    WS_POPUP = 0x80000000
    WS_CAPTION = 0x00C00000

    def __init__(self, backend=None, platform=None):
        super().__init__()
        self.surfaces = []
        self.surface_map = {}
        self.backend = backend or create_window_tracker_backend(platform)
        self.available = self.backend.available
        self.own_pid = self.backend.own_pid

    def refresh(self):
        if not self.available:
            self.surfaces = []
            self.surface_map = {}
            return
        collected = []
        for snapshot in self.backend.enumerate_window_snapshots():
            surface = self.build_surface(snapshot)
            if surface:
                collected.append(surface)
        self.surfaces = collected
        self.surface_map = {surface.hwnd: surface for surface in collected}

    def get_surface_by_hwnd(self, hwnd):
        return self.surface_map.get(int(hwnd or 0))

    def get_screen_for_surface(self, surface):
        return QApplication.screenAt(surface.rect.center()) or QApplication.primaryScreen()

    def get_screen_rect_for_surface(self, surface):
        screen = self.get_screen_for_surface(surface)
        return screen.geometry() if screen else None

    def build_surface(self, snapshot):
        return build_window_surface(
            snapshot,
            own_pid=self.own_pid,
            min_window_width=self.MIN_WINDOW_WIDTH,
            min_window_height=self.MIN_WINDOW_HEIGHT,
            ws_ex_toolwindow=self.WS_EX_TOOLWINDOW,
            ws_child=self.WS_CHILD,
            ws_popup=self.WS_POPUP,
            ws_caption=self.WS_CAPTION,
        )

    def is_surface_perch_allowed(self, surface):
        return rule_is_surface_perch_allowed(surface.rect, self.get_screen_rect_for_surface(surface))

    def can_actor_perch_on_surface(self, surface, actor):
        actor_snapshot = WindowActorSnapshot.from_actor(actor)
        return can_actor_perch_on_surface(
            surface,
            self.get_screen_rect_for_surface(surface),
            actor_snapshot.height,
        )

    def can_pet_perch_on_surface(self, surface, pet):
        return self.can_actor_perch_on_surface(surface, pet)

    def get_top_surface_at_point(self, x, y):
        point = QPoint(int(x), int(y))
        for surface in self.surfaces:
            if surface.rect.contains(point):
                return surface
        return None

    def is_surface_top_segment_visible(self, surface, center_x, actor_width=0):
        return rule_is_surface_top_segment_visible(
            surface,
            center_x,
            self.get_screen_rect_for_surface(surface),
            self.get_top_surface_at_point,
            actor_width=actor_width,
            top_edge_inset=self.TOP_EDGE_INSET,
            top_edge_y_offsets=self.TOP_EDGE_Y_OFFSETS,
        )

    def get_surface_visible_center_x(self, surface, actor_width=0, preferred_center_x=None, exact=False):
        return choose_surface_visible_center_x(
            surface,
            self.is_surface_perch_allowed(surface),
            self.is_surface_top_segment_visible,
            actor_width=actor_width,
            preferred_center_x=preferred_center_x,
            exact=exact,
            top_edge_inset=self.TOP_EDGE_INSET,
        )

    def build_actor_snapshot(self, pet):
        return WindowActorSnapshot.from_actor(pet)

    def is_actor_perch_position_visible(self, surface, actor, preferred_center_x=None):
        actor_snapshot = self.build_actor_snapshot(actor)
        if preferred_center_x is None:
            preferred_center_x = actor_snapshot.center_x
        return self.get_surface_visible_center_x(
            surface,
            actor_width=actor_snapshot.width,
            preferred_center_x=preferred_center_x,
            exact=True,
        ) is not None

    def find_drop_surface_for_actor(self, actor):
        if not self.surfaces:
            return None
        actor_snapshot = self.build_actor_snapshot(actor)
        return select_drop_surface(
            actor_snapshot,
            self.surfaces,
            can_actor_perch_on_surface=lambda surface: self.can_actor_perch_on_surface(surface, actor_snapshot),
            get_surface_visible_center_x=self.get_surface_visible_center_x,
            snap_top_tolerance=self.SNAP_TOP_TOLERANCE,
            snap_depth_limit=self.SNAP_DEPTH_LIMIT,
        )

    def find_drop_surface(self, pet):
        return self.find_drop_surface_for_actor(pet)

    def find_flight_surface_for_actor(self, actor):
        if not self.surfaces:
            return None
        actor_snapshot = self.build_actor_snapshot(actor)
        return select_flight_surface(
            actor_snapshot,
            self.surfaces,
            can_actor_perch_on_surface=lambda surface: self.can_actor_perch_on_surface(surface, actor_snapshot),
            get_surface_visible_center_x=self.get_surface_visible_center_x,
        )

    def find_flight_surface(self, pet):
        return self.find_flight_surface_for_actor(pet)

    def is_surface_flight_allowed(self, surface):
        return self.is_surface_perch_allowed(surface)
