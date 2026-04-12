import ctypes
import os
import random
import sys
from ctypes import wintypes
from dataclasses import dataclass

from PyQt6.QtCore import QObject, QPoint, QRect
from PyQt6.QtWidgets import QApplication


@dataclass
class WindowSurface:
    hwnd: int
    rect: QRect
    title: str
    class_name: str

    def perch_y(self, actor_height):
        return self.rect.top() - actor_height

    def clamp_actor_x(self, x, actor_width):
        min_x = self.rect.left()
        max_x = self.rect.left() + self.rect.width() - actor_width
        if max_x < min_x:
            return min_x
        return max(min_x, min(max_x, int(x)))

    def contains_x(self, x):
        return self.rect.left() <= int(x) <= (self.rect.left() + self.rect.width())


class WindowTracker(QObject):
    MIN_WINDOW_WIDTH = 180
    MIN_WINDOW_HEIGHT = 80
    SNAP_TOP_TOLERANCE = 110
    SNAP_DEPTH_LIMIT = 70
    TOP_EDGE_INSET = 18
    TOP_EDGE_Y_OFFSETS = (8, 18, 28)
    GWL_STYLE = -16
    GWL_EXSTYLE = -20
    WS_EX_TOOLWINDOW = 0x00000080
    WS_CHILD = 0x40000000
    WS_POPUP = 0x80000000
    WS_CAPTION = 0x00C00000
    GW_OWNER = 4
    GA_ROOT = 2
    DWMWA_EXTENDED_FRAME_BOUNDS = 9
    DWMWA_CLOAKED = 14

    def __init__(self):
        super().__init__()
        self.surfaces = []
        self.surface_map = {}
        self.available = (sys.platform == "win32")
        self.own_pid = os.getpid()
        if self.available:
            self.user32 = ctypes.windll.user32
            self.dwmapi = getattr(ctypes.windll, "dwmapi", None)
            self.enum_windows_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        else:
            self.user32 = None
            self.dwmapi = None
            self.enum_windows_proc = None

    def refresh(self):
        if not self.available:
            self.surfaces = []
            self.surface_map = {}
            return

        collected = []

        @self.enum_windows_proc
        def enum_proc(hwnd, _lparam):
            surface = self.build_surface(hwnd)
            if surface:
                collected.append(surface)
            return True

        self.user32.EnumWindows(enum_proc, 0)
        self.surfaces = collected
        self.surface_map = {surface.hwnd: surface for surface in collected}

    def get_surface_by_hwnd(self, hwnd):
        return self.surface_map.get(int(hwnd or 0))

    def get_screen_for_surface(self, surface):
        return QApplication.screenAt(surface.rect.center()) or QApplication.primaryScreen()

    def get_window_rect(self, hwnd):
        rect = wintypes.RECT()
        if self.dwmapi:
            try:
                hr = self.dwmapi.DwmGetWindowAttribute(
                    hwnd,
                    self.DWMWA_EXTENDED_FRAME_BOUNDS,
                    ctypes.byref(rect),
                    ctypes.sizeof(rect),
                )
                if hr == 0:
                    return rect
            except Exception:
                pass
        self.user32.GetWindowRect(hwnd, ctypes.byref(rect))
        return rect

    def get_window_text(self, hwnd):
        length = self.user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return ""
        buffer = ctypes.create_unicode_buffer(length + 1)
        self.user32.GetWindowTextW(hwnd, buffer, len(buffer))
        return buffer.value

    def get_class_name(self, hwnd):
        buffer = ctypes.create_unicode_buffer(256)
        self.user32.GetClassNameW(hwnd, buffer, len(buffer))
        return buffer.value

    def is_window_cloaked(self, hwnd):
        if not self.dwmapi:
            return False
        cloaked = wintypes.DWORD()
        try:
            hr = self.dwmapi.DwmGetWindowAttribute(
                hwnd,
                self.DWMWA_CLOAKED,
                ctypes.byref(cloaked),
                ctypes.sizeof(cloaked),
            )
            return hr == 0 and bool(cloaked.value)
        except Exception:
            return False

    def build_surface(self, hwnd):
        hwnd = self.user32.GetAncestor(hwnd, self.GA_ROOT)
        if not hwnd:
            return None
        if not self.user32.IsWindowVisible(hwnd) or self.user32.IsIconic(hwnd):
            return None
        if self.is_window_cloaked(hwnd):
            return None

        pid = wintypes.DWORD()
        self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == self.own_pid:
            return None

        if self.user32.GetWindow(hwnd, self.GW_OWNER):
            return None

        style = self.user32.GetWindowLongW(hwnd, self.GWL_STYLE)
        ex_style = self.user32.GetWindowLongW(hwnd, self.GWL_EXSTYLE)
        if style & self.WS_CHILD:
            return None
        if ex_style & self.WS_EX_TOOLWINDOW:
            return None
        if (style & self.WS_POPUP) and not (style & self.WS_CAPTION):
            return None

        class_name = self.get_class_name(hwnd)
        if class_name in {"Shell_TrayWnd", "Progman", "WorkerW"}:
            return None

        title = self.get_window_text(hwnd).strip()
        if not title:
            return None

        rect = self.get_window_rect(hwnd)
        width = rect.right - rect.left
        height = rect.bottom - rect.top
        if width < self.MIN_WINDOW_WIDTH or height < self.MIN_WINDOW_HEIGHT:
            return None

        return WindowSurface(
            hwnd=int(hwnd),
            rect=QRect(rect.left, rect.top, width, height),
            title=title,
            class_name=class_name,
        )

    def is_surface_perch_allowed(self, surface):
        screen = self.get_screen_for_surface(surface)
        if not screen:
            return True
        screen_rect = screen.geometry()
        nearly_full_width = surface.rect.width() >= int(screen_rect.width() * 0.97)
        nearly_full_height = surface.rect.height() >= int(screen_rect.height() * 0.94)
        near_top = surface.rect.top() <= (screen_rect.top() + 10)
        covers_screen = (
            surface.rect.left() <= (screen_rect.left() + 12) and
            surface.rect.right() >= (screen_rect.right() - 12) and
            surface.rect.bottom() >= (screen_rect.bottom() - 12)
        )
        return not ((near_top and nearly_full_width and nearly_full_height) or covers_screen)

    def can_pet_perch_on_surface(self, surface, pet):
        if not self.is_surface_perch_allowed(surface):
            return False
        screen = self.get_screen_for_surface(surface)
        if not screen:
            return True
        min_perch_y = screen.geometry().top() - int(pet.height() * 0.65)
        return surface.perch_y(pet.height()) >= min_perch_y

    def get_top_surface_at_point(self, x, y):
        point = QPoint(int(x), int(y))
        for surface in self.surfaces:
            if surface.rect.contains(point):
                return surface
        return None

    def is_surface_top_segment_visible(self, surface, center_x, actor_width=0):
        if not surface.contains_x(center_x):
            return False
        screen = self.get_screen_for_surface(surface)
        if not screen:
            return False
        screen_rect = screen.geometry()
        span = max(14, int(actor_width * 0.22)) if actor_width else 0
        probe_xs = [int(center_x)]
        if span:
            probe_xs.extend([int(center_x - span), int(center_x + span)])
        for probe_x in probe_xs:
            if probe_x < (surface.rect.left() + self.TOP_EDGE_INSET):
                return False
            if probe_x > (surface.rect.right() - self.TOP_EDGE_INSET):
                return False
            point_visible = False
            for y_offset in self.TOP_EDGE_Y_OFFSETS:
                probe_y = min(surface.rect.bottom() - 6, surface.rect.top() + y_offset)
                point = QPoint(probe_x, probe_y)
                if not screen_rect.contains(point):
                    continue
                top_surface = self.get_top_surface_at_point(probe_x, probe_y)
                if top_surface and top_surface.hwnd == surface.hwnd:
                    point_visible = True
                    break
            if not point_visible:
                return False
        return True

    def get_surface_visible_center_x(self, surface, actor_width=0, preferred_center_x=None, exact=False):
        if not self.is_surface_perch_allowed(surface):
            return None
        half_width = actor_width // 2 if actor_width else 0
        min_center = surface.rect.left() + max(self.TOP_EDGE_INSET, half_width)
        max_center = surface.rect.right() - max(self.TOP_EDGE_INSET, actor_width - half_width)
        if max_center < min_center:
            return None

        if preferred_center_x is not None:
            preferred_center_x = max(min_center, min(max_center, int(preferred_center_x)))

        candidates = []
        if preferred_center_x is not None:
            candidates.append(preferred_center_x)
        if not exact:
            center_x = surface.rect.center().x()
            left_mid = surface.rect.left() + int(surface.rect.width() * 0.35)
            right_mid = surface.rect.left() + int(surface.rect.width() * 0.65)
            for probe_x in [center_x, left_mid, right_mid]:
                probe_x = max(min_center, min(max_center, int(probe_x)))
                candidates.append(probe_x)

        seen = set()
        for probe_x in candidates:
            if probe_x in seen:
                continue
            seen.add(probe_x)
            if self.is_surface_top_segment_visible(surface, probe_x, actor_width=actor_width):
                return probe_x
        return None

    def find_drop_surface(self, pet):
        if not self.surfaces:
            return None
        pet_rect = pet.geometry()
        probe_x = pet_rect.center().x()
        pet_bottom = pet_rect.bottom()
        pet_top = pet_rect.top()

        for surface in self.surfaces:
            if not self.can_pet_perch_on_surface(surface, pet):
                continue
            if not surface.contains_x(probe_x):
                continue
            top_y = surface.rect.top()
            if pet_bottom < (top_y - self.SNAP_TOP_TOLERANCE):
                continue
            if pet_bottom > (top_y + self.SNAP_DEPTH_LIMIT):
                continue
            if pet_top > (top_y + self.SNAP_DEPTH_LIMIT):
                continue
            if not self.get_surface_visible_center_x(
                surface,
                actor_width=pet.width(),
                preferred_center_x=probe_x,
                exact=True,
            ):
                continue
            return surface
        return None

    def find_flight_surface(self, pet):
        if not self.surfaces:
            return None
        pet_center = pet.geometry().center()
        candidates = []
        for surface in self.surfaces:
            if not self.can_pet_perch_on_surface(surface, pet):
                continue
            if surface.rect.width() < max(160, int(pet.width() * 0.55)):
                continue
            anchor_center_x = self.get_surface_visible_center_x(
                surface,
                actor_width=pet.width(),
                preferred_center_x=pet_center.x(),
            )
            if anchor_center_x is None:
                continue
            perch_y = surface.perch_y(pet.height())
            if perch_y >= pet.y() - 30:
                continue
            dx = abs(anchor_center_x - pet_center.x())
            dy = abs(perch_y - pet.y())
            score = dx + (dy * 0.8)
            candidates.append((score, surface))
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0])
        top_candidates = candidates[: min(3, len(candidates))]
        weights = [1.0 / max(1.0, score + 1.0) for score, _surface in top_candidates]
        return random.choices(
            [surface for _score, surface in top_candidates],
            weights=weights,
            k=1,
        )[0]

    def is_surface_flight_allowed(self, surface):
        return self.is_surface_perch_allowed(surface)

