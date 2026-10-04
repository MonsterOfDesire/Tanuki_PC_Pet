from dataclasses import dataclass

from PyQt6.QtCore import QPoint, QRect
from PyQt6.QtGui import QRegion
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
    near_left_edge: bool = False
    near_right_edge: bool = False
    dock_edge: str = "none"


class DesktopGeometry:
    EDGE_MARGIN = 18

    @staticmethod
    def get_virtual_rect():
        return get_total_virtual_geometry()

    @classmethod
    def get_screen_for_widget(cls, widget):
        return cls.get_screen_for_rect(widget.geometry())

    @classmethod
    def get_screen_for_rect(cls, rect, screens=None):
        candidates = tuple(
            QApplication.screens() if screens is None else screens
        )
        if not candidates:
            return QApplication.primaryScreen()

        rect_center = rect.center()
        ranked = []
        for screen in candidates:
            screen_rect = screen.geometry()
            intersection = screen_rect.intersected(rect)
            intersection_area = max(0, intersection.width()) * max(
                0,
                intersection.height(),
            )
            center = screen_rect.center()
            distance_squared = (
                (center.x() - rect_center.x()) ** 2
                + (center.y() - rect_center.y()) ** 2
            )
            ranked.append(
                (
                    -intersection_area,
                    distance_squared,
                    screen_rect.left(),
                    screen_rect.top(),
                    screen,
                )
            )
        return min(ranked, key=lambda item: item[:-1])[-1]

    @classmethod
    def get_horizontal_movement_bounds(
        cls,
        rect,
        *,
        screens=None,
        selected_screen=None,
    ):
        """Return the contiguous on-screen corridor at the actor's height.

        A virtual desktop is a bounding rectangle and may contain large gaps
        when one monitor sits above another.  Treating that bounding rectangle
        as walkable lets pets disappear into those gaps.  Screens that really
        touch at the actor's vertical centre remain one corridor, so ordinary
        side-by-side monitor roaming keeps working.
        """
        candidates = tuple(
            QApplication.screens() if screens is None else screens
        )
        actor_width = max(0, int(rect.width()))
        selected_screen = selected_screen or cls.get_screen_for_rect(
            rect,
            screens=candidates,
        )
        if selected_screen is None:
            virtual_rect = get_total_virtual_geometry()
            return (
                virtual_rect.left(),
                virtual_rect.right() - actor_width,
            )

        selected_rect = selected_screen.geometry()
        probe_y = rect.center().y()
        intervals = []
        for screen in candidates:
            screen_rect = screen.geometry()
            if screen_rect.top() <= probe_y <= screen_rect.bottom():
                intervals.append(
                    (screen_rect.left(), screen_rect.right())
                )

        corridor_left = selected_rect.left()
        corridor_right = selected_rect.right()
        changed = True
        while changed:
            changed = False
            for interval_left, interval_right in intervals:
                if (
                    interval_right < corridor_left - 1
                    or interval_left > corridor_right + 1
                ):
                    continue
                expanded_left = min(corridor_left, interval_left)
                expanded_right = max(corridor_right, interval_right)
                if (
                    expanded_left != corridor_left
                    or expanded_right != corridor_right
                ):
                    corridor_left = expanded_left
                    corridor_right = expanded_right
                    changed = True
        return corridor_left, corridor_right - actor_width

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
        left_bound, right_bound = cls.get_horizontal_movement_bounds(
            widget.geometry(),
            selected_screen=screen,
        )
        top_bound = screen_rect.top()
        bottom_bound = screen_rect.bottom() - actor_height
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
    def get_drag_target_screen_rect(cls, cursor_x, cursor_y, previous_screen_rect=None):
        """Remember the cursor's screen, not the lagging character's screen.

        Keep a geometry copy instead of a QScreen reference so hot-unplugging
        a display cannot leave a deleted native object in interaction state.
        A cursor in a desktop gap does not authorize a monitor handoff.
        """
        screen_rects = tuple(screen.geometry() for screen in QApplication.screens())
        cursor = QPoint(int(cursor_x), int(cursor_y))
        for rect in screen_rects:
            if rect.contains(cursor):
                return QRect(rect)
        for rect in screen_rects:
            if rect == previous_screen_rect:
                return QRect(rect)
        return None

    @classmethod
    def clamp_drag_position(
        cls, widget, x, y, padding=0, top_visible_ratio=0.35,
        *, target_screen_rect=None,
    ):
        screens = tuple(QApplication.screens())
        proposed = QRect(
            int(x),
            int(y),
            int(widget.width()),
            int(widget.height()),
        )
        screen = next(
            (candidate for candidate in screens
             if candidate.geometry() == target_screen_rect),
            None,
        ) or cls.get_screen_for_rect(proposed, screens=screens)
        if screen is None:
            surface = cls.get_surface_snapshot(widget)
            min_y = surface.top_bound - int(
                widget.height() * (1.0 - top_visible_ratio)
            )
            return (
                surface.clamp_x(x, padding=padding),
                max(min_y, min(surface.bottom_bound, int(y))),
            )

        screen_rect = screen.geometry()
        min_x = screen_rect.left() + int(padding)
        max_x = screen_rect.right() - int(widget.width()) - int(padding) + 1
        if max_x < min_x:
            min_x = screen_rect.left()
            max_x = screen_rect.right() - int(widget.width()) + 1
        min_y = screen_rect.top() - int(
            widget.height() * (1.0 - top_visible_ratio)
        )
        max_y = screen_rect.bottom() - int(widget.height()) + 1
        return (
            max(min_x, min(max_x, int(x))),
            max(min_y, min(max_y, int(y))),
        )

    @classmethod
    def clamp_drag_follow_position(cls, widget, x, y, *, target_screen_rect=None):
        """Allow smooth screen seams; project desktop gaps onto the target.

        The whole actor may straddle touching screens while following. If a
        step enters an invisible gap, hand off to the cursor's selected screen
        once instead of repeatedly pinning the actor to its previous display.
        Ordinary autonomous movement does not use this policy.
        """
        screens = tuple(QApplication.screens())
        if target_screen_rect is None or not any(
            screen.geometry() == target_screen_rect for screen in screens
        ):
            return cls.clamp_drag_position(widget, x, y)

        proposed = QRect(int(x), int(y), int(widget.width()), int(widget.height()))
        visible_region = QRegion()
        for screen in screens:
            visible_region = visible_region.united(QRegion(screen.geometry()))
        if QRegion(proposed).subtracted(visible_region).isEmpty():
            return int(x), int(y)
        current_screen = cls.get_screen_for_rect(widget.geometry(), screens=screens)
        is_handoff = current_screen is not None and (
            current_screen.geometry() != target_screen_rect
        )
        return cls.clamp_drag_position(
            widget, x, y, target_screen_rect=target_screen_rect,
            # A gap handoff should land fully in view; normal dragging at the
            # same screen's upper edge retains the existing partial-top policy.
            top_visible_ratio=1.0 if is_handoff else 0.35,
        )
