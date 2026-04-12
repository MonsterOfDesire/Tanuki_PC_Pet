from dataclasses import dataclass

from PyQt6.QtCore import QRect
from PyQt6.QtWidgets import QApplication


def get_total_virtual_geometry():
    rect = QRect()
    for screen in QApplication.screens():
        rect = rect.united(screen.geometry())
    return rect


@dataclass
class SurfaceSnapshot:
    virtual_rect: QRect
    screen_rect: QRect
    available_rect: QRect
    actor_width: int
    actor_height: int
    floor_top_y: int
    screen_floor_top_y: int
    left_bound: int
    right_bound: int
    top_bound: int
    bottom_bound: int
    dock_edge: str
    dock_thickness: int
    on_floor: bool
    near_left_edge: bool
    near_right_edge: bool

    def clamp_x(self, x, padding=0):
        min_x = self.left_bound + padding
        max_x = self.right_bound - padding
        if max_x < min_x:
            min_x = self.left_bound
            max_x = self.right_bound
        return max(min_x, min(max_x, int(x)))

    def clamp_y(self, y):
        return max(self.top_bound, min(self.bottom_bound, int(y)))


@dataclass
class PetMovementState:
    intent: str = "idle"
    locomotion: str = "idle"
    anchor: str = "floor"
    support_surface: str = "desktop_floor"
    edge_side: str = "none"
    near_left_edge: bool = False
    near_right_edge: bool = False
    can_attach_edge: bool = False
    dock_edge: str = "none"


class DesktopGeometry:
    EDGE_MARGIN = 18

    @staticmethod
    def get_virtual_rect():
        return get_total_virtual_geometry()

    @classmethod
    def get_screen_for_widget(cls, widget):
        return QApplication.screenAt(widget.geometry().center()) or QApplication.primaryScreen()

    @staticmethod
    def detect_dock_edge(screen_rect, available_rect):
        dock_margins = {
            "left": max(0, available_rect.left() - screen_rect.left()),
            "top": max(0, available_rect.top() - screen_rect.top()),
            "right": max(0, screen_rect.right() - available_rect.right()),
            "bottom": max(0, screen_rect.bottom() - available_rect.bottom()),
        }
        edge = "none"
        thickness = 0
        for edge_name, value in dock_margins.items():
            if value > thickness:
                edge = edge_name
                thickness = value
        return edge, thickness

    @classmethod
    def get_surface_snapshot(cls, widget, edge_margin=None):
        if edge_margin is None:
            edge_margin = cls.EDGE_MARGIN
        virtual_rect = cls.get_virtual_rect()
        screen = cls.get_screen_for_widget(widget)
        screen_rect = screen.geometry() if screen else virtual_rect
        available_rect = screen.availableGeometry() if screen else screen_rect
        actor_width = widget.width()
        actor_height = widget.height()
        left_bound = virtual_rect.left()
        right_bound = virtual_rect.right() - actor_width
        top_bound = virtual_rect.top()
        bottom_bound = virtual_rect.bottom() - actor_height
        floor_top_y = available_rect.bottom() - actor_height
        screen_floor_top_y = screen_rect.bottom() - actor_height
        dock_edge, dock_thickness = cls.detect_dock_edge(screen_rect, available_rect)
        x = widget.x()
        y = widget.y()
        return SurfaceSnapshot(
            virtual_rect=virtual_rect,
            screen_rect=screen_rect,
            available_rect=available_rect,
            actor_width=actor_width,
            actor_height=actor_height,
            floor_top_y=floor_top_y,
            screen_floor_top_y=screen_floor_top_y,
            left_bound=left_bound,
            right_bound=right_bound,
            top_bound=top_bound,
            bottom_bound=bottom_bound,
            dock_edge=dock_edge,
            dock_thickness=dock_thickness,
            on_floor=y >= floor_top_y,
            near_left_edge=x <= left_bound + edge_margin,
            near_right_edge=x >= right_bound - edge_margin,
        )

    @classmethod
    def clamp_widget_position(cls, widget, x, y, padding=0):
        surface = cls.get_surface_snapshot(widget)
        return surface.clamp_x(x, padding=padding), surface.clamp_y(y)

    @classmethod
    def clamp_drag_position(cls, widget, x, y, padding=0, top_visible_ratio=0.35):
        surface = cls.get_surface_snapshot(widget)
        min_y = surface.top_bound - int(widget.height() * (1.0 - top_visible_ratio))
        max_y = surface.bottom_bound
        clamped_y = max(min_y, min(max_y, int(y)))
        return surface.clamp_x(x, padding=padding), clamped_y
