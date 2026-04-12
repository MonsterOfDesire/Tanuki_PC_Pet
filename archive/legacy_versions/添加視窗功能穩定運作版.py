import os
import sys
import random
import math
import time
import json
import re
import ctypes
from dataclasses import dataclass
from ctypes import wintypes

# --- 環境路徑初始化 ---
def get_base_path():
    # 判定程式是純 py 執行還是被 Nuitka 編譯後的環境
    if "__compiled__" in globals():
        return os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.dirname(os.path.abspath(__file__))

from PyQt6.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox, QProgressBar
from PyQt6.QtCore import Qt, QPoint, QSize, QTimer, QPropertyAnimation, QRect, QObject, QEasingCurve, QVariantAnimation, \
    pyqtSignal
from PyQt6.QtGui import QMovie, QPainter, QColor, QPixmap, QImage
from pynput import mouse

def check_assets_integrity(required_folders):
    assets_dir = AssetManager.get_resource_path("assets_cropped")
    missing = []
    for folder in required_folders:
        path = os.path.join(assets_dir, folder)
        if not os.path.exists(path):
            missing.append(folder)
    if missing:
        msg = f"偵測到關鍵素材缺失：\n{', '.join(missing)}\n\n請確保 assets_cropped 資料夾完整！"
        QMessageBox.critical(None, "系統錯誤", msg)
        sys.exit()

def get_total_virtual_geometry():
    rect = QRect()
    for screen in QApplication.screens():
        rect = rect.united(screen.geometry())
    return rect

class SimulationClock:
    def __init__(self):
        self.speed = 1.0
        self.real_anchor = time.perf_counter()
        self.sim_anchor = time.time()
        self.timer_specs = []

    def now(self):
        elapsed = time.perf_counter() - self.real_anchor
        return self.sim_anchor + (elapsed * self.speed)

    def set_speed(self, speed):
        speed = max(1.0, float(speed))
        self.sim_anchor = self.now()
        self.real_anchor = time.perf_counter()
        self.speed = speed
        self.apply_registered_timers()

    def register_timer(self, timer, base_interval_ms):
        if timer is None:
            return
        base_interval_ms = max(1, int(base_interval_ms))
        self.timer_specs.append((timer, base_interval_ms))
        self.apply_timer_interval(timer, base_interval_ms)

    def apply_timer_interval(self, timer, base_interval_ms):
        interval = max(1, int(round(base_interval_ms / self.speed)))
        timer.setInterval(interval)

    def apply_registered_timers(self):
        active_specs = []
        for timer, base_interval_ms in self.timer_specs:
            try:
                self.apply_timer_interval(timer, base_interval_ms)
                active_specs.append((timer, base_interval_ms))
            except RuntimeError:
                continue
        self.timer_specs = active_specs

SIM_CLOCK = SimulationClock()

def app_now():
    return SIM_CLOCK.now()

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

class GlobalMouseListener(QObject):
    request_slide_out = pyqtSignal()
    def __init__(self, dashboard):
        super().__init__()
        self.dashboard = dashboard
        self.request_slide_out.connect(self.dashboard.slide_out, Qt.ConnectionType.QueuedConnection)
        self.listener = mouse.Listener(on_click=self.on_click)
        self.listener.start()
    def on_click(self, x, y, button, pressed):
        if pressed and self.dashboard.is_expanded:
            ratio = self.dashboard.devicePixelRatio()
            logic_point = QPoint(int(x / ratio), int(y / ratio))
            if not self.dashboard.geometry().contains(logic_point):
                self.request_slide_out.emit()

class AssetManager:
    """
    負責解析檔名、載入 GIF 幀、縮放並快取素材。
    檔名規則解析：purpose_action-mood.gif (例如: move_walk-happy.gif)
    """
    def __init__(self, character_path, scale_factor=0.4):
        self.character_path = character_path
        self.scale_factor = scale_factor
        self.assets = {}
        self.asset_records = {}
        self.manifest_data = {}
        self.refresh_assets()

    def load_manifest(self):
        manifest_path = os.path.join(self.character_path, "manifest_edit.json")
        if not os.path.exists(manifest_path):
            return {}
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                raw = f.read()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                sanitized = re.sub(r",(\s*[}\]])", r"\1", raw)
                data = json.loads(sanitized)
            manifest = {}
            for file_name, meta in data.items():
                if isinstance(meta, dict):
                    manifest[file_name] = self.normalize_manifest_entry(meta)
            return manifest
        except Exception as e:
            print(f"讀取 manifest 失敗 {manifest_path}: {e}")
            return {}

    def normalize_manifest_entry(self, meta):
        bands = []
        for raw_band in meta.get("band", []):
            if not isinstance(raw_band, str):
                continue
            normalized = raw_band.replace(".", ",")
            for token in normalized.split(","):
                band = token.strip()
                if band in {"normal", "low", "severe"} and band not in bands:
                    bands.append(band)
        contexts = []
        for raw_context in meta.get("contexts", []):
            if not isinstance(raw_context, str):
                continue
            context = raw_context.strip()
            if context and context not in contexts:
                contexts.append(context)
        try:
            weight = float(meta.get("weight", 1.0))
        except (TypeError, ValueError):
            weight = 1.0
        return {
            "band": bands,
            "contexts": contexts,
            "weight": max(0.0, weight),
        }

    def get_mood_band(self, mood_score):
        if mood_score < 20:
            return "severe"
        if mood_score < 50:
            return "low"
        return "normal"

    def get_record(self, purpose, action_type, mood):
        return self.asset_records.get(purpose, {}).get(action_type, {}).get(mood)

    def get_action_keys_for_context(self, purpose, mood_score=None, context=None):
        keys = []
        for action_type, mood_map in self.asset_records.get(purpose, {}).items():
            for mood_tag in mood_map.keys():
                record = self.get_record(purpose, action_type, mood_tag)
                if self.is_record_eligible(record, mood_score=mood_score, context=context):
                    keys.append(action_type)
                    break
        return keys

    def get_record_weight(self, record):
        if not record:
            return 1.0
        meta = record.get("manifest") or {}
        return max(0.0, float(meta.get("weight", 1.0) or 0.0))

    def is_record_eligible(self, record, mood_score=None, context=None):
        if not record:
            return False
        meta = record.get("manifest") or {}
        bands = meta.get("band") or []
        if mood_score is not None and bands:
            if self.get_mood_band(mood_score) not in bands:
                return False
        contexts = meta.get("contexts") or []
        if context and contexts and context not in contexts:
            return False
        return True

    def choose_weighted_result(self, results):
        if not results:
            return None
        weights = [max(0.0, result[3]) for result in results]
        if any(weight > 0 for weight in weights):
            chosen = random.choices(results, weights=weights, k=1)[0]
        else:
            chosen = random.choice(results)
        return chosen[0], chosen[1], chosen[2]

    def get_safe_frames(self, purpose, mood_list, forbidden=None):
        if forbidden is None: forbidden = []
        if purpose not in self.assets: return self.get_any_available_frames()
        available_types = self.assets[purpose]
        type_keys = list(available_types.keys())
        random.shuffle(type_keys)
        for mood_tag in mood_list:
            for t_key in type_keys:
                mood_map = available_types[t_key]
                if mood_tag in mood_map:
                    return mood_map[mood_tag]
        for t_key in type_keys:
            mood_map = available_types[t_key]
            safe_keys = [k for k in mood_map.keys() if k not in forbidden]
            if safe_keys:
                if "normal" in safe_keys: return mood_map["normal"]
                return mood_map[random.choice(safe_keys)]
        return self.get_any_available_frames()

    def get_safe_reaction_result(self, purpose, mood_list, forbidden=None):
        if forbidden is None:
            forbidden = []
        if purpose not in self.assets:
            return None
        available_types = self.assets[purpose]
        type_keys = list(available_types.keys())
        random.shuffle(type_keys)
        for mood_tag in mood_list:
            for action_type in type_keys:
                record = self.get_record(purpose, action_type, mood_tag)
                if record:
                    return record["frames"], action_type, mood_tag
        for action_type in type_keys:
            mood_map = available_types[action_type]
            safe_keys = [tag for tag in mood_map.keys() if tag not in forbidden]
            if safe_keys:
                chosen_mood = "normal" if "normal" in safe_keys else random.choice(safe_keys)
                record = self.get_record(purpose, action_type, chosen_mood)
                if record:
                    return record["frames"], action_type, chosen_mood
        fallback = self.get_any_available_frames()
        if fallback:
            return fallback, "default", ""
        return None

    def get_mood_rules(self, mood_score, is_adult=False):
        if mood_score < 20:
            if is_adult:
                return (
                    ["scold", "sad", "angry", "exhausted"],
                    ["awkward", "think", "hurry", "effort", "sleep"],
                    ["happy", "smile", "confidence", "cool", "cry", "hard-cry", "scared"],
                )
            return (
                ["scold", "hard-cry", "cry", "exhausted", "scared"],
                ["sad", "angry", "awkward", "think", "hurry", "effort", "sleep"],
                ["happy", "smile", "confidence", "cool"],
            )
        if mood_score < 50:
            return (
                ["angry", "sad", "think", "awkward", "hurry", "effort", "sleep"],
                ["cry", "hard-cry", "scold", "exhausted", "scared"],
                ["happy", "smile", "confidence", "cool"],
            )
        return (
            ["happy", "smile", "confidence", "cool", "glance"],
            ["awkward", "think"],
            ["cry", "hard-cry", "sad", "angry", "scold"],
        )

    def get_frames_by_score(self, purpose, action_type=None, mood_score=60.0, is_adult=False, context=None):
        if purpose not in self.assets:
            return self.get_any_available_frames(), "default", ""

        available_types = self.assets[purpose]
        priority_chain, fallback_chain, forbidden = self.get_mood_rules(mood_score, is_adult=is_adult)

        if action_type in available_types:
            for mood_tag in priority_chain + fallback_chain:
                record = self.get_record(purpose, action_type, mood_tag)
                if self.is_record_eligible(record, mood_score=mood_score, context=context):
                    return record["frames"], action_type, mood_tag

        type_keys = list(available_types.keys())
        if action_type in type_keys:
            type_keys.remove(action_type)
            type_keys.insert(0, action_type)
        for mood_tag in priority_chain + fallback_chain:
            matches = []
            for t_key in type_keys:
                record = self.get_record(purpose, t_key, mood_tag)
                if self.is_record_eligible(record, mood_score=mood_score, context=context):
                    matches.append((record["frames"], t_key, mood_tag, self.get_record_weight(record)))
            weighted = self.choose_weighted_result(matches)
            if weighted:
                return weighted

        target_action = action_type if action_type in available_types else random.choice(list(available_types.keys()))
        safe_results = []
        normal_result = None
        for mood_tag in available_types[target_action].keys():
            if mood_tag in forbidden:
                continue
            record = self.get_record(purpose, target_action, mood_tag)
            if not self.is_record_eligible(record, mood_score=mood_score, context=context):
                continue
            result = (record["frames"], target_action, mood_tag, self.get_record_weight(record))
            if mood_tag == "normal":
                normal_result = result
            safe_results.append(result)
        if normal_result:
            return normal_result[0], normal_result[1], normal_result[2]
        weighted = self.choose_weighted_result(safe_results)
        if weighted:
            return weighted
        if self.manifest_data:
            return None
        return self.get_any_available_frames(), "default", ""

    def get_frames_for_action_by_score(self, purpose, action_type, mood_score=60.0, is_adult=False, context=None):
        if purpose not in self.assets or action_type not in self.assets[purpose]:
            return None

        priority_chain, fallback_chain, forbidden = self.get_mood_rules(mood_score, is_adult=is_adult)

        for mood_tag in priority_chain + fallback_chain:
            record = self.get_record(purpose, action_type, mood_tag)
            if self.is_record_eligible(record, mood_score=mood_score, context=context):
                return record["frames"], action_type, mood_tag

        safe_results = []
        normal_result = None
        for mood_tag in self.assets[purpose][action_type].keys():
            if mood_tag in forbidden:
                continue
            record = self.get_record(purpose, action_type, mood_tag)
            if not self.is_record_eligible(record, mood_score=mood_score, context=context):
                continue
            result = (record["frames"], action_type, mood_tag, self.get_record_weight(record))
            if mood_tag == "normal":
                normal_result = result
            safe_results.append(result)
        if normal_result:
            return normal_result[0], normal_result[1], normal_result[2]
        weighted = self.choose_weighted_result(safe_results)
        if weighted:
            return weighted

        return None

    def get_frames_for_action_by_preferences(self, purpose, action_type, preferred_moods, forbidden=None, mood_score=None, context=None):
        if purpose not in self.assets or action_type not in self.assets[purpose]:
            return None
        for mood_tag in preferred_moods:
            record = self.get_record(purpose, action_type, mood_tag)
            if self.is_record_eligible(record, mood_score=mood_score, context=context):
                return record["frames"], action_type, mood_tag
        if forbidden is None:
            forbidden = []
        safe_results = []
        normal_result = None
        for mood_tag in self.assets[purpose][action_type].keys():
            if mood_tag in forbidden:
                continue
            record = self.get_record(purpose, action_type, mood_tag)
            if not self.is_record_eligible(record, mood_score=mood_score, context=context):
                continue
            result = (record["frames"], action_type, mood_tag, self.get_record_weight(record))
            if mood_tag == "normal":
                normal_result = result
            safe_results.append(result)
        if normal_result:
            return normal_result[0], normal_result[1], normal_result[2]
        weighted = self.choose_weighted_result(safe_results)
        if weighted:
            return weighted
        return None

    def get_contextual_result(self, purpose, context=None, preferred_moods=None):
        if purpose not in self.asset_records:
            return None
        preferred_moods = preferred_moods or []
        preferred_results = []
        fallback_results = []
        for action_type, mood_map in self.asset_records[purpose].items():
            for mood_tag, record in mood_map.items():
                meta = record.get("manifest") or {}
                contexts = meta.get("contexts") or []
                if context and contexts and context not in contexts:
                    continue
                result = (
                    record["frames"],
                    action_type,
                    mood_tag,
                    self.get_record_weight(record),
                )
                if mood_tag in preferred_moods:
                    preferred_results.append(result)
                else:
                    fallback_results.append(result)
        weighted = self.choose_weighted_result(preferred_results)
        if weighted:
            return weighted
        return self.choose_weighted_result(fallback_results)

    @staticmethod
    def get_resource_path(relative_path):
        base = get_base_path()
        return os.path.join(base, relative_path)

    # 修改 AssetManager 內的 refresh_assets
    def refresh_assets(self):
        # 遍歷資料夾，將 GIF 拆解為 (目的, 動作, 情緒) 三層字典
        # 這是優化的重點：讓之後的 AI 邏輯可以精確查找「對應」的動作
        if not os.path.exists(self.character_path): return
        self.assets = {}
        self.asset_records = {}
        self.manifest_data = self.load_manifest()
        files = [f for f in os.listdir(self.character_path) if f.endswith(".gif")]
        for file in files:
            try:
                base_name, _ = os.path.splitext(file)
                mood = base_name.split("-", 1)[1] if "-" in base_name else ""
                name_part = base_name.split("-", 1)[0]

                parts = name_part.split("_")
                purpose = parts[0]
                action_type = "_".join(parts[1:]) if len(parts) > 1 else "default"

                frames = self.extract_frames(os.path.join(self.character_path, file))
                if frames:
                    if purpose not in self.assets: self.assets[purpose] = {}
                    if purpose not in self.asset_records: self.asset_records[purpose] = {}
                    if action_type not in self.assets[purpose]: self.assets[purpose][action_type] = {}
                    if action_type not in self.asset_records[purpose]: self.asset_records[purpose][action_type] = {}
                    self.assets[purpose][action_type][mood] = frames
                    self.asset_records[purpose][action_type][mood] = {
                        "frames": frames,
                        "file_name": file,
                        "manifest": self.manifest_data.get(file, {}),
                    }
            except Exception as e:
                print(f"解析失敗 {file}: {e}")

    def extract_frames(self, gif_path):
        movie = QMovie(gif_path)
        movie.setCacheMode(QMovie.CacheMode.CacheAll)
        movie.jumpToFrame(0)
        frames = []
        count = movie.frameCount()
        for i in range(max(1, count)):
            movie.jumpToFrame(i)
            img = movie.currentImage()
            if img.isNull(): break
            scaled_img = img.scaled(
                img.size() * self.scale_factor,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            frames.append(QPixmap.fromImage(scaled_img))
        return frames

    def get_any_available_frames(self):
        for p in self.assets.values():
            for t in p.values():
                for f in t.values(): return f
        return []

    def get_specific_frames(self, purpose, action_type, mood, mood_score=None, context=None):
        """嚴格匹配：只有當目的、動作、情緒完全一致時才回傳"""
        record = self.get_record(purpose, action_type, mood)
        if self.is_record_eligible(record, mood_score=mood_score, context=context):
            return record["frames"]
        return None

    def get_action_keys(self, purpose):
        return list(self.assets.get(purpose, {}).keys())

    def has_action(self, purpose, action_type):
        return action_type in self.assets.get(purpose, {})

class ConfigStore(QObject):
    def __init__(self, config_path=None):
        super().__init__()
        self.config_path = config_path or AssetManager.get_resource_path("config.json")
        self.dashboard = None
        self.pets_dict = {}
        self.loaded_state = self.load()
        self.last_saved_payload = ""

    def load(self):
        if not os.path.exists(self.config_path):
            return {}
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception as e:
            print(f"讀取 config.json 失敗 {self.config_path}: {e}")
            return {}

    def bind(self, dashboard, pets_dict):
        self.dashboard = dashboard
        self.pets_dict = pets_dict
        dashboard.config_store = self
        self.apply_loaded_state()
        self.last_saved_payload = self.serialize_state(self.capture_state())

    def schedule_save(self):
        return

    def serialize_state(self, state):
        return json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True)

    def safe_index(self, value, default, size):
        try:
            index = int(value)
        except (TypeError, ValueError):
            index = default
        return max(0, min(size - 1, index))

    def clamp_pet_position(self, pet, x, y):
        return DesktopGeometry.clamp_widget_position(pet, x, y)

    def apply_loaded_state(self):
        if not self.dashboard or not self.pets_dict:
            return

        dashboard_state = self.loaded_state.get("dashboard", {})
        self.dashboard.set_care_enabled(dashboard_state.get("care_feature_enabled", self.dashboard.care_feature_enabled), save=False)
        self.dashboard.teio_dur_idx = self.safe_index(
            dashboard_state.get("teio_dur_idx", self.dashboard.teio_dur_idx),
            self.dashboard.teio_dur_idx,
            len(self.dashboard.teio_dur_list),
        )
        self.dashboard.tsuyoshi_dur_idx = self.safe_index(
            dashboard_state.get("tsuyoshi_dur_idx", self.dashboard.tsuyoshi_dur_idx),
            self.dashboard.tsuyoshi_dur_idx,
            len(self.dashboard.tsuyoshi_dur_list),
        )
        self.dashboard.time_scale_idx = self.safe_index(
            dashboard_state.get("time_scale_idx", self.dashboard.time_scale_idx),
            self.dashboard.time_scale_idx,
            len(self.dashboard.time_scale_options),
        )
        self.dashboard.display_scale_idx = self.safe_index(
            dashboard_state.get("display_scale_idx", self.dashboard.display_scale_idx),
            self.dashboard.display_scale_idx,
            len(self.dashboard.display_scale_options),
        )
        self.dashboard.update_duration_buttons()
        self.dashboard.update_time_scale_buttons()
        self.dashboard.update_display_scale_buttons()
        self.dashboard.set_time_scale_index(self.dashboard.time_scale_idx)
        self.dashboard.apply_display_scale()
        self.dashboard.apply_social_settings()

        pets_state = self.loaded_state.get("pets", {})
        for pet_name, info in self.pets_dict.items():
            pet = info["pet"]
            state = pets_state.get(pet_name, {})
            pet.user_visible = bool(state.get("user_visible", pet.user_visible))

            x = state.get("x", pet.x())
            y = state.get("y", pet.y())
            clamped_x, clamped_y = self.clamp_pet_position(pet, x, y)
            pet.move(clamped_x, clamped_y)

            if pet.user_visible:
                pet.show()
            else:
                pet.hide()
            pet.refresh_movement_state()

            toggle_button = info.get("toggle_button")
            if toggle_button:
                toggle_button.blockSignals(True)
                toggle_button.setChecked(pet.user_visible)
                toggle_button.blockSignals(False)

    def capture_state(self):
        dashboard_state = {}
        if self.dashboard:
            dashboard_state = {
                "care_feature_enabled": bool(self.dashboard.care_feature_enabled),
                "teio_dur_idx": int(self.dashboard.teio_dur_idx),
                "tsuyoshi_dur_idx": int(self.dashboard.tsuyoshi_dur_idx),
                "time_scale_idx": int(self.dashboard.time_scale_idx),
                "display_scale_idx": int(self.dashboard.display_scale_idx),
            }

        pets_state = {}
        for pet_name, info in self.pets_dict.items():
            pet = info["pet"]
            pets_state[pet_name] = {
                "x": int(pet.x()),
                "y": int(pet.y()),
                "user_visible": bool(getattr(pet, "user_visible", pet.isVisible())),
            }

        return {
            "schema_version": 1,
            "dashboard": dashboard_state,
            "pets": pets_state,
        }

    def save_now(self, force=False):
        if not self.dashboard or not self.pets_dict:
            return
        state = self.capture_state()
        payload = self.serialize_state(state)
        if not force and payload == self.last_saved_payload:
            return
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                f.write(payload)
            self.last_saved_payload = payload
        except Exception as e:
            print(f"寫入 config.json 失敗 {self.config_path}: {e}")

class Dashboard(QWidget):
    DURATION_BTN_STYLE = (
        "QPushButton { background: #f3f3f3; color: #222; border-radius: 8px; padding: 6px 10px; border: 1px solid #999; }"
        "QPushButton:checked { background: #91e08f; border: 1px solid #4a8f48; font-weight: bold; }"
    )
    SECTION_LABEL_STYLE = "color: white; background: rgba(0,0,0,150); padding: 6px 8px; border-radius: 6px;"

    def __init__(self, target_rect, pets_dict):
        super().__init__()
        self.is_expanded = False
        self.config_store = None
        self.care_feature_enabled = True  # c. 開啟/關閉大人照護功能
        self.time_scale_options = [1, 2, 4, 8]
        self.time_scale_idx = 0
        self.time_scale_buttons = []
        self.display_scale_options = [1.0, 1.5, 2.0, 3.0]
        self.display_scale_idx = 0
        self.display_scale_buttons = []
        self.teio_dur_list = [2, 5, 10, 20, 30]
        self.teio_dur_idx = 3  # 預設 20s (索引3)
        self.tsuyoshi_dur_list = [2, 10, 20, 40, 60]
        self.tsuyoshi_dur_idx = 2  # 預設 20s (索引2)
        self.teio_duration_buttons = []
        self.tsuyoshi_duration_buttons = []
        self.target_rect = target_rect
        self.pets_dict = pets_dict
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.layout = QVBoxLayout()
        self.layout.setSpacing(10)  # 拉開組件間距
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.title_label = QLabel("狸貓控制中心")
        self.title_label.setStyleSheet("color: white; background: rgba(0,0,0,150); padding: 5px; border-radius: 5px;")
        self.layout.addWidget(self.title_label)
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: white; background: rgba(70,90,120,190); padding: 6px 8px; border-radius: 6px;")
        self.status_label.hide()
        self.layout.addWidget(self.status_label)
        # --- 新增功能按鈕區 ---
        self.layout.addWidget(self.make_section_label("全域設定"))

        self.layout.addWidget(self.make_section_label("時間流速"))
        speed_row = self.create_option_selector(
            self.time_scale_options,
            self.time_scale_buttons,
            lambda value: f"{value}x",
            self.set_time_scale_index,
        )
        self.layout.addLayout(speed_row)

        self.layout.addWidget(self.make_section_label("顯示比例"))
        scale_row = self.create_option_selector(
            self.display_scale_options,
            self.display_scale_buttons,
            lambda value: f"{value:g}x",
            self.set_display_scale_index,
        )
        self.layout.addLayout(scale_row)

        self.btn_care = QPushButton("照護功能: 開啟")
        self.btn_care.clicked.connect(self.toggle_care)
        self.layout.addWidget(self.btn_care)

        self.layout.addWidget(self.make_section_label("帝寶社交冷卻"))
        teio_row = self.create_duration_selector("teio", self.teio_dur_list)
        self.layout.addLayout(teio_row)

        self.layout.addWidget(self.make_section_label("鶴寶社交冷卻"))
        tsuyoshi_row = self.create_duration_selector("tsuyoshi", self.tsuyoshi_dur_list)
        self.layout.addLayout(tsuyoshi_row)
        for folder_name, info in self.pets_dict.items():
            container = QWidget()
            v_box = QVBoxLayout(container)
            v_box.setSpacing(4)
            v_box.setContentsMargins(0, 0, 0, 0)

            btn = QPushButton(f"召喚 {info['name']}")
            btn.setFixedHeight(35)
            btn.setCheckable(True)
            btn.setChecked(info["pet"].user_visible)
            btn.toggled.connect(lambda checked, p=info["pet"]: self.handle_pet_toggle(p, checked))
            btn.setStyleSheet(
                "QPushButton { background: white; border-radius: 8px; padding: 8px; } QPushButton:checked { background: #aaffaa; }")

            # 1. 先建立實體
            mood_bar = QProgressBar()
            mood_bar.setRange(0, 100)
            mood_bar.setTextVisible(False)
            mood_bar.setFixedHeight(6)
            mood_bar.setStyleSheet(
                "QProgressBar::chunk { background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff4444, stop:1 #44ff44); } QProgressBar { background-color: #333; border-radius: 3px; }")

            # 2. 【關鍵修正】先存入字典
            info["mood_bar"] = mood_bar
            info["toggle_button"] = btn

            # 3. 再從字典讀取並加入佈局 (或是直接加入 mood_bar 變數也可以)
            v_box.addWidget(btn)
            v_box.addWidget(mood_bar)
            self.layout.addWidget(container)
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.refresh_mood_bars)
        self.update_timer.start(500)
        SIM_CLOCK.register_timer(self.update_timer, 500)
        self.btn_exit = QPushButton("關閉系統")
        self.btn_exit.clicked.connect(self.begin_shutdown)
        self.layout.addWidget(self.btn_exit)
        self.setLayout(self.layout)
        # 調整面板整體尺寸
        ratio = self.devicePixelRatio()
        base_w, base_h = 360, 780  # 定義基準寬高
        max_h = max(560, target_rect.height() - 20)
        self.setFixedSize(int(base_w * ratio), int(min(base_h, max_h) * ratio))
        self.update_positions(target_rect)
        self.move(self.hide_pos)
        self.anim = QPropertyAnimation(self, b"pos")
        self.anim.setDuration(400)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.update_duration_buttons()
        self.update_time_scale_buttons()
        self.update_display_scale_buttons()
        self.update_care_button_text()
    def refresh_mood_bars(self):
        for info in self.pets_dict.values():
            info["mood_bar"].setValue(int(info["pet"].mood_score))

    def make_section_label(self, text):
        label = QLabel(text)
        label.setStyleSheet(self.SECTION_LABEL_STYLE)
        return label

    def update_care_button_text(self):
        self.btn_care.setText(f"照護功能: {'開啟' if self.care_feature_enabled else '關閉'}")

    def show_shutdown_status(self):
        self.status_label.setText("正在儲存設定...")
        self.status_label.show()
        self.btn_exit.setEnabled(False)
        self.btn_exit.setText("正在關閉...")
        self.is_expanded = True
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.move(self.show_pos)
        self.show()
        self.raise_()
        QApplication.processEvents()

    def begin_shutdown(self):
        self.show_shutdown_status()
        if self.config_store:
            self.config_store.save_now(force=True)
        QApplication.quit()

    def set_care_enabled(self, enabled, save=True):
        self.care_feature_enabled = bool(enabled)
        self.update_care_button_text()

    def toggle_care(self):
        self.set_care_enabled(not self.care_feature_enabled)

    def handle_pet_toggle(self, pet, checked):
        pet.user_visible = bool(checked)
        if checked:
            if not (pet.care_lock_mode == "hidden" and pet.is_under_care(app_now())):
                pet.show()
        else:
            pet.hide()

    def create_duration_selector(self, char, durations):
        row = QHBoxLayout()
        row.setSpacing(6)
        button_bucket = self.teio_duration_buttons if char == "teio" else self.tsuyoshi_duration_buttons
        for idx, seconds in enumerate(durations):
            btn = QPushButton(f"{seconds}s")
            btn.setCheckable(True)
            btn.setMinimumWidth(48)
            btn.setStyleSheet(self.DURATION_BTN_STYLE)
            btn.clicked.connect(lambda checked=False, c=char, i=idx: self.set_duration(c, i))
            button_bucket.append(btn)
            row.addWidget(btn)
        return row

    def create_option_selector(self, values, button_bucket, formatter, handler):
        row = QHBoxLayout()
        row.setSpacing(6)
        for idx, value in enumerate(values):
            btn = QPushButton(formatter(value))
            btn.setCheckable(True)
            btn.setMinimumWidth(48)
            btn.setStyleSheet(self.DURATION_BTN_STYLE)
            btn.clicked.connect(lambda checked=False, i=idx: handler(i))
            button_bucket.append(btn)
            row.addWidget(btn)
        return row

    def set_duration(self, char, index):
        if char == "teio":
            self.teio_dur_idx = index
        else:
            self.tsuyoshi_dur_idx = index
        self.update_duration_buttons()
        self.apply_social_settings()

    def update_duration_buttons(self):
        for idx, btn in enumerate(self.teio_duration_buttons):
            btn.setChecked(idx == self.teio_dur_idx)
        for idx, btn in enumerate(self.tsuyoshi_duration_buttons):
            btn.setChecked(idx == self.tsuyoshi_dur_idx)

    def update_time_scale_buttons(self):
        for idx, btn in enumerate(self.time_scale_buttons):
            btn.setChecked(idx == self.time_scale_idx)

    def update_display_scale_buttons(self):
        for idx, btn in enumerate(self.display_scale_buttons):
            btn.setChecked(idx == self.display_scale_idx)

    def get_time_scale(self):
        return float(self.time_scale_options[self.time_scale_idx])

    def set_time_scale_index(self, index):
        self.time_scale_idx = max(0, min(len(self.time_scale_options) - 1, int(index)))
        self.update_time_scale_buttons()
        SIM_CLOCK.set_speed(self.get_time_scale())

    def get_display_scale_multiplier(self):
        return float(self.display_scale_options[self.display_scale_idx])

    def set_display_scale_index(self, index):
        self.display_scale_idx = max(0, min(len(self.display_scale_options) - 1, int(index)))
        self.update_display_scale_buttons()
        self.apply_display_scale()

    def apply_display_scale(self):
        multiplier = self.get_display_scale_multiplier()
        for info in self.pets_dict.values():
            pet = info.get("pet")
            if pet:
                pet.apply_display_scale(multiplier)

    def get_social_cooldown_label_seconds(self, pet_name):
        if pet_name == "Tokai Teio":
            return self.teio_dur_list[self.teio_dur_idx]
        if pet_name == "Tsurumaru Tsuyoshi":
            return self.tsuyoshi_dur_list[self.tsuyoshi_dur_idx]
        return 0

    def get_social_cooldown_seconds(self, pet_name):
        duration = self.get_social_cooldown_label_seconds(pet_name)
        return float(duration) if duration else 0.0

    def apply_social_settings(self):
        teio = self.pets_dict.get("Tokai Teio", {}).get("pet")
        tsuyoshi = self.pets_dict.get("Tsurumaru Tsuyoshi", {}).get("pet")
        if teio:
            teio.social_cooldown_duration = self.get_social_cooldown_seconds("Tokai Teio")
        if tsuyoshi:
            tsuyoshi.social_cooldown_duration = self.get_social_cooldown_seconds("Tsurumaru Tsuyoshi")
    def update_positions(self, rect):
        # 使用 self.width() 和 self.height() 獲取當前實際像素大小
        w = self.width()
        h = self.height()

        # 計算顯示位置 (貼齊工作列上方)
        self.show_pos = QPoint(rect.left(), rect.bottom() - h)
        # 計算隱藏位置 (縮到左側螢幕外)
        self.hide_pos = QPoint(rect.left() - w - 10, rect.bottom() - h)
    def slide_in(self, pets, sensor):
        self.is_expanded = True
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.anim.setEndValue(self.show_pos); self.anim.start(); self.raise_()
    def slide_out(self):
        if self.is_expanded:
            self.is_expanded = False
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            self.anim.setEndValue(self.hide_pos); self.anim.start()

class SensorZone(QWidget):
    def __init__(self, dashboard):
        super().__init__()
        self.dashboard = dashboard
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.progress = 0.0
        self.glow_anim = QVariantAnimation(self)
        self.glow_anim.setDuration(2000)
        self.glow_anim.setStartValue(0.0); self.glow_anim.setEndValue(1.0)
        self.glow_anim.valueChanged.connect(self.update_progress)
        self.glow_anim.finished.connect(self.on_finished)
    def update_progress(self, value):
        self.progress = value; self.update()
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setBrush(QColor(40, 40, 40, 80)); painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(self.rect())
        if self.progress > 0:
            fill_h = int(self.height() * self.progress)
            painter.setBrush(QColor(100, 255, 100, 200))
            painter.drawRect(0, self.height() - fill_h, self.width(), fill_h)
    def on_finished(self):
        if self.progress >= 0.99: self.dashboard.slide_in([], self)
        self.progress = 0.0; self.update()
    def enterEvent(self, event):
        if not self.dashboard.is_expanded: self.glow_anim.start()
    def leaveEvent(self, event):
        self.glow_anim.stop(); self.progress = 0.0; self.update()

class TanukiPet(QWidget):
    """
    使用明確的優先序來處理 AI，避免救助 / 模仿 / 隨機行為互相覆蓋。
    """
    ADULT_NAMES = {"Symboli Rudolf", "Sirius Symboli", "Air Groove"}
    CHILD_NAMES = {"Tokai Teio", "Tsurumaru Tsuyoshi"}
    AUTONOMOUS_FLY_DISABLED_NAMES = {"Tsurumaru Tsuyoshi"}
    CHILD_TOKEN_MAP = {
        "Tokai Teio": ["Teio"],
        "Tsurumaru Tsuyoshi": ["Tsuyoshi"],
    }
    DISTRESS_MOODS = {"sad", "cry", "hard-cry"}
    SEVERE_MOODS = {"scold", "hard-cry", "cry", "exhausted", "scared"}
    ADULT_SEVERE_MOODS = {"scold", "sad", "angry", "exhausted"}
    EDGE_INTERACTION_ENABLED = False

    def __init__(self, char_id, char_folder, scale=0.8, dashboard_instance=None):
        super().__init__()
        self.char_id = char_id; self.name = char_id
        self.character_path = char_folder
        self.base_scale = float(scale)
        self.display_scale_multiplier = 1.0
        self.asset_manager = AssetManager(char_folder, scale_factor=self.get_effective_scale())
        self.current_frames = []; self.frame_index = 0; self.direction = 1
        self.dragging = False; self.original_face_left = True
        self.user_visible = True
        self.mood_score = 60.0; self.mood_state = "normal"; self.drag_start_time = 0
        self.click_count = 0
        self.is_angry_locked = False
        self.click_reset_timer = QTimer(self)
        self.click_reset_timer.setSingleShot(True)
        self.click_reset_timer.timeout.connect(self.reset_clicks)
        self.lock_timer = QTimer(self)
        self.lock_timer.setSingleShot(True)
        self.lock_timer.timeout.connect(self.unlock_interaction)
        self.state = "idle"
        self.state_timer = 0
        self.current_purpose = ""
        self.is_adult = self.name in self.ADULT_NAMES
        self.lonely_timer = 0
        self.setFixedSize(int(600 * self.get_effective_scale()), int(600 * self.get_effective_scale()))
        self.social_mode = "none"
        self.social_target = None
        self.social_started_at = 0.0
        self.social_timer_frames = 0
        self.social_cooldown_end = 0.0
        # --- 性格差異化參數設定 ---
        self.social_distance = 600  # 預設感應距離
        self.social_cooldown_duration = 5.0  # 預設冷卻時間(秒)

        if self.name == "Tokai Teio":  # 帝寶：愛湊熱鬧，感應遠，冷卻短
            self.social_distance = 600
            self.social_cooldown_duration = 10.0
        elif self.name == "Tsurumaru Tsuyoshi":  # 鶴寶：害羞體弱，感應近，冷卻長
            self.social_distance = 350
            self.social_cooldown_duration = 10.0
        self.current_action_tag = "stand"
        self.current_mood_tag = "happy"

        # --- 星星相關 ---
        self.star_pixmap = QPixmap(AssetManager.get_resource_path("star.png"))
        self.star_opacity = 0.0
        self.star_y_offset = 0
        self.star_anim_counter = 0
        self.star_timer = QTimer(self)
        self.star_timer.timeout.connect(self.update_star_animation)
        SIM_CLOCK.register_timer(self.star_timer, 30)

        # --- 抱抱飲料互動相關 ---
        self.dashboard = dashboard_instance  # 傳入 dashboard 引用以讀取設定
        self.window_tracker = None
        self.perched_window_hwnd = 0
        self.window_perch_offset_x = 0
        self.window_perch_mode = "idle"
        self.window_perch_origin = "manual"
        self.window_perch_end_time = 0.0
        self.flight_mode = "none"
        self.flight_target_hwnd = 0
        self.flight_target_x = 0
        self.flight_target_y = 0
        self.flight_cooldown_end = 0.0
        self.is_recovering = False
        self.recovery_end_time = 0.0
        self.recovery_motion_mode = "stay"
        self.stationary_move_mode = False
        self.stationary_move_key = ""
        self.movement_state = PetMovementState()
        self.edge_mode = "none"
        self.edge_side = "none"
        self.edge_target_y = 0
        self.edge_return_x = 0
        self.edge_pause_until = 0.0
        self.edge_cooldown_end = 0.0
        self.is_hugging = False
        self.care_mode = "none"
        self.care_target = None
        self.care_end_time = 0.0
        self.care_cooldown_end = 0.0
        self.care_move_direction = 0
        self.care_plan = "auto"
        self.care_partner = None
        self.care_lock_mode = "none"
        self.care_lock_end_time = 0.0

        self.bar_opacity = 0.0
        self.fade_anim = QVariantAnimation(self)
        self.fade_anim.setDuration(300)
        self.fade_anim.valueChanged.connect(self.update_bar_opacity)
        self.heart_pixmap = QPixmap(AssetManager.get_resource_path("heart.png"))
        self.show_heart = False; self.heart_opacity = 0.0; self.heart_y_offset = 0
        self.heart_anim = QVariantAnimation(self)
        self.heart_anim.setDuration(1000)
        self.heart_anim.setStartValue(0.0); self.heart_anim.setEndValue(1.0)
        self.heart_anim.valueChanged.connect(self.animate_heart)
        self.heart_anim.finished.connect(lambda: setattr(self, 'show_heart', False))
        self.vy = 0.0; self.gravity = 1.2; self.bounce = -0.3
        self.radius = (100 * self.get_effective_scale()); self.mass = 2 if self.is_adult else 0.8
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.anim_timer = QTimer(self); self.anim_timer.timeout.connect(self.next_frame); self.anim_timer.start(80)
        SIM_CLOCK.register_timer(self.anim_timer, 80)
        self.change_state("idle", "stand")
        self.last_x = self.x()
        self.stuck_count = 0
        self.refresh_movement_state()
        self.show()

    def get_effective_scale(self):
        return self.base_scale * self.display_scale_multiplier

    def apply_display_scale(self, multiplier):
        multiplier = max(0.5, float(multiplier))
        if abs(self.display_scale_multiplier - multiplier) < 0.001:
            return

        old_center_x = self.geometry().center().x()
        old_bottom_y = self.y() + self.height()
        old_visible = self.isVisible()
        old_signature = (self.current_purpose, self.current_action_tag, self.current_mood_tag)

        self.display_scale_multiplier = multiplier
        self.asset_manager = AssetManager(self.character_path, scale_factor=self.get_effective_scale())
        self.setFixedSize(int(600 * self.get_effective_scale()), int(600 * self.get_effective_scale()))
        self.radius = (100 * self.get_effective_scale())

        target_x = old_center_x - (self.width() // 2)
        target_y = old_bottom_y - self.height()

        if self.perched_window_hwnd and self.window_tracker:
            surface = self.window_tracker.get_surface_by_hwnd(self.perched_window_hwnd)
            if surface and self.window_tracker.can_pet_perch_on_surface(surface, self):
                target_x = surface.clamp_actor_x(old_center_x - (self.width() // 2), self.width())
                self.window_perch_offset_x = target_x - surface.rect.left()
                target_y = self.get_window_perch_y(surface)
            else:
                self.detach_from_window_surface()
        elif self.flight_mode == "to_window" and self.window_tracker:
            surface = self.window_tracker.get_surface_by_hwnd(self.flight_target_hwnd)
            if surface:
                anchor_center_x = self.window_tracker.get_surface_visible_center_x(
                    surface,
                    actor_width=self.width(),
                    preferred_center_x=old_center_x,
                )
                if anchor_center_x is not None:
                    self.flight_target_x = surface.clamp_actor_x(anchor_center_x - (self.width() // 2), self.width())
                    self.flight_target_y = self.get_window_perch_y(surface)
                    self.window_perch_offset_x = self.flight_target_x - surface.rect.left()

        clamped_x, clamped_y = DesktopGeometry.clamp_widget_position(self, target_x, target_y)
        self.move(clamped_x, clamped_y)

        purpose, action_type, mood = old_signature
        frames = None
        if purpose and action_type and mood:
            frames = self.asset_manager.get_specific_frames(purpose, action_type, mood, mood_score=self.mood_score)
        if frames:
            self.apply_animation_result(purpose, (frames, action_type, mood))
        elif self.state == "move":
            self.change_state("move")
        else:
            self.change_state("idle", "stand")

        if old_visible and self.user_visible:
            self.show()
        elif not self.user_visible:
            self.hide()
        self.refresh_movement_state()
        self.update()

    def reset_clicks(self): self.click_count = 0
    def unlock_interaction(self):
        self.is_angry_locked = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.change_state("idle", "stand")
    def update_bar_opacity(self, value): self.bar_opacity = value; self.update()
    def animate_heart(self, value): self.heart_opacity = 1.0 - (value ** 2); self.heart_y_offset = int(value * 60); self.update()
    def pop_heart(self):
        if not self.heart_pixmap.isNull(): self.show_heart = True; self.heart_anim.start()

    def get_social_cooldown_seconds(self):
        if self.dashboard:
            cooldown = self.dashboard.get_social_cooldown_seconds(self.name)
            if cooldown:
                return cooldown
        return self.social_cooldown_duration

    def get_social_duration_frames(self, mode):
        if mode == "following":
            return random.randint(200, 400)
        if mode == "mimicking":
            return random.randint(60, 80)
        return 0

    def get_child_tokens(self):
        return self.CHILD_TOKEN_MAP.get(self.name, [self.name])

    def distance_to(self, other):
        return math.hypot(
            self.geometry().center().x() - other.geometry().center().x(),
            self.geometry().center().y() - other.geometry().center().y()
        )

    def get_surface_snapshot(self):
        return DesktopGeometry.get_surface_snapshot(self)

    def refresh_movement_state(self, surface=None):
        if surface is None:
            surface = self.get_surface_snapshot()
        if self.vy != 0:
            intent = "falling"
            locomotion = "airborne"
            anchor = "air"
            support_surface = "air"
            edge_side = "none"
        else:
            if self.flight_mode != "none":
                intent = f"flight:{self.flight_mode}"
                locomotion = "moving"
                anchor = "air"
                support_surface = "air"
                edge_side = "none"
            elif self.perched_window_hwnd:
                intent = "perched:window"
                locomotion = "moving" if self.state == "move" else "idle"
                anchor = "window_top"
                support_surface = "window_top"
                edge_side = "none"
            elif self.edge_mode != "none":
                intent = f"edge:{self.edge_mode}"
                locomotion = "idle" if self.edge_mode == "perch" else "moving"
                if self.edge_mode == "return_taskbar":
                    anchor = "air"
                    support_surface = "air"
                else:
                    anchor = f"{self.edge_side}_edge" if self.edge_side in {"left", "right"} else "edge"
                    support_surface = "edge"
                edge_side = self.edge_side
            elif self.care_mode != "none":
                intent = f"care:{self.care_mode}"
                edge_side = "none"
            elif self.social_mode != "none":
                intent = f"social:{self.social_mode}"
                edge_side = "none"
            elif self.is_recovering:
                intent = "recovery"
                edge_side = "none"
            else:
                intent = self.state or "idle"
                edge_side = "none"
            if self.flight_mode == "none" and self.edge_mode == "none" and not self.perched_window_hwnd:
                locomotion = "moving" if self.state == "move" else "idle"
                support_surface = "desktop_floor" if surface.on_floor else "screen_space"
                if surface.on_floor and surface.near_left_edge:
                    anchor = "left_edge_ready"
                elif surface.on_floor and surface.near_right_edge:
                    anchor = "right_edge_ready"
                else:
                    anchor = "floor" if surface.on_floor else "air"
        self.movement_state = PetMovementState(
            intent=intent,
            locomotion=locomotion,
            anchor=anchor,
            support_surface=support_surface,
            edge_side=edge_side,
            near_left_edge=surface.near_left_edge,
            near_right_edge=surface.near_right_edge,
            can_attach_edge=(not self.dragging and self.vy == 0 and self.care_mode == "none" and self.edge_mode == "none" and self.flight_mode == "none" and not self.perched_window_hwnd),
            dock_edge=surface.dock_edge,
        )
        return self.movement_state

    def get_edge_attach_target(self):
        state = self.refresh_movement_state()
        if not state.can_attach_edge:
            return None
        if state.anchor == "left_edge_ready":
            return "left"
        if state.anchor == "right_edge_ready":
            return "right"
        return None

    def get_taskbar_walk_y(self):
        surface = self.get_surface_snapshot()
        if surface.dock_edge == "bottom" and surface.dock_thickness > 0:
            return surface.screen_floor_top_y
        return surface.floor_top_y

    def get_airborne_top_bound(self, visible_ratio=0.35):
        surface = self.get_surface_snapshot()
        return surface.top_bound - int(self.height() * (1.0 - visible_ratio))

    def get_window_perch_y(self, surface):
        return max(self.get_airborne_top_bound(), surface.perch_y(self.height()))

    def apply_drag_animation(self):
        preferred_moods = ["sad", "exhausted", "angry", "scold", "awkward", "think", "cry", "hard-cry"]
        result = self.asset_manager.get_contextual_result("drag", context="drag", preferred_moods=preferred_moods)
        if not result:
            result = self.asset_manager.get_frames_by_score(
                "drag",
                mood_score=self.mood_score,
                is_adult=self.is_adult,
                context="drag",
            )
        return self.apply_animation_result("drag", result)

    def get_window_perch_candidates(self):
        candidates = []
        for action_type in [
            "sit", "sit_talk", "sit_read",
            "side", "side_face", "side_face_hand", "side_face_stretch",
            "side_rub", "side_hug", "side_stretch", "side_play",
            "side_fan", "side_ready", "side_stand",
            "drink", "eat", "get",
            "stand", "observe", "rest", "lie", "squat",
            "hear", "photo", "photo_ready", "dance_uma", "dance_three",
        ]:
            if self.asset_manager.has_action("idle", action_type):
                candidates.append(("idle", action_type))
        return self.expand_candidates_with_context("idle", candidates or self.get_idle_candidates(), context="random")

    def get_window_walk_candidates(self):
        candidates = []
        for action_type in ["walk", "jog", "sneak"]:
            if self.asset_manager.has_action("move", action_type):
                candidates.append(("move", action_type))
        if candidates:
            return candidates
        for action_type in self.asset_manager.get_action_keys("move"):
            if action_type in {"fly_up"}:
                continue
            if action_type not in {"walk", "jog", "sneak"}:
                candidates.append(("move", action_type))
        return candidates

    def can_fly_freely(self):
        return self.name not in self.AUTONOMOUS_FLY_DISABLED_NAMES and bool(self.get_free_fly_candidates())

    def has_free_fly_animation(self):
        return self.can_fly_freely()

    def get_free_fly_candidates(self):
        candidates = []
        for action_type in ["fly_up", "fly"]:
            if self.asset_manager.has_action("move", action_type):
                candidates.append(("move", action_type))
        return candidates

    def move_flight_toward(self, target_x, target_y, speed=None):
        if speed is None:
            speed = max(2.8, self.get_base_speed() + 1.2)
        dx = float(target_x - self.x())
        dy = float(target_y - self.y())
        dist = math.hypot(dx, dy)
        if dist <= max(10.0, speed * 1.4):
            self.move(int(round(target_x)), int(round(target_y)))
            return True

        travel = min(float(speed), dist)
        ratio = travel / dist if dist > 0 else 1.0
        next_x = self.x() + (dx * ratio)
        next_y = self.y() + (dy * ratio)
        if abs(dx) > 18:
            next_y += math.sin((app_now() * 6.0) + (self.frame_index * 0.35)) * 1.4

        surface = self.get_surface_snapshot()
        min_y = self.get_airborne_top_bound()
        next_x = surface.clamp_x(next_x)
        next_y = max(min_y, min(surface.bottom_bound, int(round(next_y))))
        self.move(next_x, next_y)
        return False

    def can_attach_to_window_surface(self):
        now = app_now()
        return (
            not self.dragging and
            self.care_mode == "none" and
            self.social_mode == "none" and
            not self.is_recovering and
            self.flight_mode == "none" and
            not self.is_under_care(now)
        )

    def detach_from_window_surface(self):
        self.perched_window_hwnd = 0
        self.window_perch_offset_x = 0
        self.window_perch_mode = "idle"
        self.window_perch_origin = "manual"
        self.window_perch_end_time = 0.0
        self.refresh_movement_state()

    def attach_to_window_surface(self, surface, origin="manual", preferred_center_x=None):
        if not surface or not self.can_attach_to_window_surface():
            return False
        if self.window_tracker and not self.window_tracker.can_pet_perch_on_surface(surface, self):
            return False
        if self.edge_mode != "none":
            self.stop_edge_mode(apply_cooldown=False)
        self.vy = 0
        self.perched_window_hwnd = surface.hwnd
        if preferred_center_x is None:
            preferred_center_x = self.geometry().center().x()
        target_x = surface.clamp_actor_x(preferred_center_x - (self.width() // 2), self.width())
        self.window_perch_offset_x = target_x - surface.rect.left()
        self.window_perch_mode = "idle"
        self.window_perch_origin = origin
        self.window_perch_end_time = app_now() + random.uniform(6.0, 12.0) if origin == "auto" else 0.0
        target_y = self.get_window_perch_y(surface)
        self.move(target_x, target_y)
        self.state = "idle"
        self.state_timer = random.randint(80, 160)
        self.ensure_candidate_animation(self.get_window_perch_candidates(), context="random")
        self.refresh_movement_state()
        return True

    def try_snap_to_window_surface(self):
        if not self.window_tracker:
            return False
        self.window_tracker.refresh()
        surface = self.window_tracker.find_drop_surface(self)
        if not surface:
            return False
        return self.attach_to_window_surface(
            surface,
            origin="manual",
            preferred_center_x=self.geometry().center().x(),
        )

    def get_window_perch_speed(self):
        return max(1, int(round(max(1.2, self.get_base_speed() * 0.8))))

    def update_window_perch(self, all_pets=None):
        if not self.perched_window_hwnd:
            return False
        if self.dragging or self.care_mode != "none" or self.social_mode != "none" or self.is_recovering:
            self.detach_from_window_surface()
            return False
        if not self.window_tracker:
            self.detach_from_window_surface()
            return False

        surface = self.window_tracker.get_surface_by_hwnd(self.perched_window_hwnd)
        if not surface:
            self.detach_from_window_surface()
            return False
        if not self.window_tracker.can_pet_perch_on_surface(surface, self):
            target_center_x = self.x() + (self.width() // 2)
            self.detach_from_window_surface()
            if not self.start_taskbar_flight(target_x=target_center_x - (self.width() // 2)):
                self.vy = 1.0
            return False

        if not self.is_adult and self.is_distressed():
            self.detach_from_window_surface()
            if not self.start_taskbar_flight(target_x=self.x()):
                self.vy = 1.0
            return False

        if self.is_adult and all_pets and self.dashboard and self.dashboard.care_feature_enabled:
            radius = None if self.name == "Sirius Symboli" else 1000
            for pet in all_pets:
                if pet == self or pet.is_adult or not pet.isVisible():
                    continue
                if pet.care_partner not in (None, self):
                    continue
                if pet.is_recovering or not pet.is_distressed():
                    continue
                dist = self.distance_to(pet)
                if radius is not None and dist > radius:
                    continue
                self.detach_from_window_surface()
                if not self.start_taskbar_flight(target_x=pet.x()):
                    self.vy = 1.0
                return False

        if self.window_perch_origin == "auto" and self.window_perch_end_time and app_now() >= self.window_perch_end_time:
            target_center_x = surface.rect.center().x() - (self.width() // 2)
            self.detach_from_window_surface()
            if not self.start_taskbar_flight(target_x=target_center_x):
                self.vy = 1.0
            return False

        target_x = surface.clamp_actor_x(surface.rect.left() + self.window_perch_offset_x, self.width())
        target_y = self.get_window_perch_y(surface)
        self.vy = 0
        max_offset = max(0, surface.rect.width() - self.width())
        self.state_timer -= 1
        if self.state_timer <= 0:
            can_walk = bool(self.get_window_walk_candidates()) and max_offset >= 30
            if can_walk and random.random() < 0.62:
                self.window_perch_mode = "move"
                self.state = "move"
                self.state_timer = random.randint(55, 120)
                if self.window_perch_offset_x <= 5:
                    self.direction = 1
                elif self.window_perch_offset_x >= max(5, max_offset - 5):
                    self.direction = -1
                elif random.random() < 0.5:
                    self.direction *= -1
                self.change_state_candidates(
                    self.get_randomized_candidates(self.get_window_walk_candidates()),
                    context="random",
                )
            else:
                self.window_perch_mode = "idle"
                self.state = "idle"
                self.state_timer = random.randint(70, 150)
                if random.random() < 0.35:
                    self.direction *= -1
                self.change_state_candidates(
                    self.get_randomized_candidates(self.get_window_perch_candidates()),
                    context="random",
                )

        if self.window_perch_mode == "move" and max_offset > 0:
            step = self.get_window_perch_speed()
            next_offset = self.window_perch_offset_x + (step * self.direction)
            if next_offset <= 0:
                next_offset = 0
                self.direction = 1
                self.window_perch_mode = "idle"
                self.state = "idle"
                self.state_timer = random.randint(60, 120)
            elif next_offset >= max_offset:
                next_offset = max_offset
                self.direction = -1
                self.window_perch_mode = "idle"
                self.state = "idle"
                self.state_timer = random.randint(60, 120)
            self.window_perch_offset_x = int(next_offset)
            target_x = surface.rect.left() + self.window_perch_offset_x
            if not self.ensure_candidate_animation(self.get_window_walk_candidates(), context="random"):
                self.window_perch_mode = "idle"
                self.state = "idle"
                self.state_timer = random.randint(70, 150)
                self.ensure_candidate_animation(self.get_window_perch_candidates(), context="random")
        else:
            self.window_perch_mode = "idle"
            self.state = "idle"
            self.ensure_candidate_animation(self.get_window_perch_candidates(), context="random")
        if self.x() != target_x or self.y() != target_y:
            self.move(target_x, target_y)
        self.refresh_movement_state()
        return True

    def can_start_window_flight(self, now=None):
        if now is None:
            now = app_now()
        if (
            self.flight_mode != "none" or
            self.perched_window_hwnd or
            self.edge_mode != "none" or
            self.dragging or
            self.vy != 0 or
            not self.isVisible() or
            self.state != "move" or
            self.care_mode != "none" or
            self.social_mode != "none" or
            self.is_recovering or
            self.is_under_care(now) or
            now < self.flight_cooldown_end or
            not self.window_tracker or
            not self.can_fly_freely()
        ):
            return False
        if self.current_purpose != "move" or self.current_action_tag not in {"fly", "fly_up"}:
            return False
        return self.window_tracker.find_flight_surface(self) is not None

    def start_window_flight(self, surface):
        if not surface:
            return False
        if not self.window_tracker:
            return False
        anchor_center_x = self.window_tracker.get_surface_visible_center_x(
            surface,
            actor_width=self.width(),
            preferred_center_x=self.geometry().center().x(),
        )
        if anchor_center_x is None:
            return False
        if self.perched_window_hwnd:
            self.detach_from_window_surface()
        if self.edge_mode != "none":
            self.stop_edge_mode(apply_cooldown=False)
        target_x = surface.clamp_actor_x(anchor_center_x - (self.width() // 2), self.width())
        target_y = self.get_window_perch_y(surface)
        self.flight_mode = "to_window"
        self.flight_target_hwnd = surface.hwnd
        self.flight_target_x = target_x
        self.flight_target_y = target_y
        self.window_perch_offset_x = target_x - surface.rect.left()
        self.vy = 0
        self.state = "move"
        self.reset_stationary_move_mode()
        self.direction = 1 if target_x >= self.x() else -1
        self.ensure_candidate_animation(self.get_free_fly_candidates(), context="random")
        self.refresh_movement_state()
        return True

    def stop_window_flight(self, apply_cooldown=True):
        was_active = self.flight_mode != "none"
        self.flight_mode = "none"
        self.flight_target_hwnd = 0
        self.flight_target_x = 0
        self.flight_target_y = 0
        if apply_cooldown and was_active:
            self.flight_cooldown_end = app_now() + random.uniform(18.0, 32.0)
        self.refresh_movement_state()

    def try_start_window_flight(self, now=None):
        if not self.window_tracker:
            return False
        if not self.can_start_window_flight(now=now):
            return False
        if random.random() >= 0.06:
            return False
        surface = self.window_tracker.find_flight_surface(self)
        if not surface:
            return False
        return self.start_window_flight(surface)

    def get_window_flight_speed(self):
        return max(2.6, self.get_base_speed() + 1.1)

    def start_taskbar_flight(self, target_x=None):
        if not self.can_fly_freely():
            return False
        surface = self.get_surface_snapshot()
        if target_x is None:
            target_x = self.x()
        self.flight_mode = "to_taskbar"
        self.flight_target_hwnd = 0
        self.flight_target_x = surface.clamp_x(target_x)
        self.flight_target_y = self.get_taskbar_walk_y()
        self.vy = 0
        self.state = "move"
        self.reset_stationary_move_mode()
        self.direction = 1 if self.flight_target_x >= self.x() else -1
        self.ensure_candidate_animation(self.get_free_fly_candidates(), context="random")
        self.refresh_movement_state()
        return True

    def update_window_flight(self):
        if self.flight_mode == "none":
            return False
        if (
            self.dragging or
            self.care_mode != "none" or
            self.social_mode != "none" or
            self.is_recovering
        ):
            self.stop_window_flight(apply_cooldown=False)
            return False
        if not self.window_tracker:
            self.stop_window_flight(apply_cooldown=False)
            return False

        if self.flight_mode == "to_taskbar":
            self.vy = 0
            self.state = "move"
            self.direction = 1 if self.flight_target_x >= self.x() else -1
            self.ensure_candidate_animation(self.get_free_fly_candidates(), context="random")
            arrived = self.move_flight_toward(
                self.flight_target_x,
                self.flight_target_y,
                speed=max(2.8, self.get_window_flight_speed()),
            )
            if arrived:
                self.move(int(self.flight_target_x), int(self.flight_target_y))
                self.stop_window_flight(apply_cooldown=True)
                self.state = "idle"
                self.state_timer = random.randint(70, 140)
                self.change_state("idle", "stand")
            else:
                self.refresh_movement_state()
            return True

        surface = self.window_tracker.get_surface_by_hwnd(self.flight_target_hwnd)
        if not surface:
            self.stop_window_flight(apply_cooldown=False)
            return False
        if not self.window_tracker.can_pet_perch_on_surface(surface, self):
            self.stop_window_flight(apply_cooldown=False)
            return False

        preferred_center_x = surface.rect.left() + self.window_perch_offset_x + (self.width() // 2)
        anchor_center_x = self.window_tracker.get_surface_visible_center_x(
            surface,
            actor_width=self.width(),
            preferred_center_x=preferred_center_x,
        )
        if anchor_center_x is None:
            self.stop_window_flight(apply_cooldown=False)
            return False

        self.flight_target_x = surface.clamp_actor_x(anchor_center_x - (self.width() // 2), self.width())
        self.flight_target_y = self.get_window_perch_y(surface)
        dx = self.flight_target_x - self.x()
        dy = self.flight_target_y - self.y()
        if math.hypot(dx, dy) <= 14:
            self.stop_window_flight(apply_cooldown=True)
            return self.attach_to_window_surface(
                surface,
                origin="auto",
                preferred_center_x=anchor_center_x,
            )

        self.vy = 0
        self.state = "move"
        self.direction = 1 if dx >= 0 else -1
        self.ensure_candidate_animation(self.get_free_fly_candidates(), context="random")
        arrived = self.move_flight_toward(
            self.flight_target_x,
            self.flight_target_y,
            speed=self.get_window_flight_speed(),
        )
        if arrived:
            self.stop_window_flight(apply_cooldown=True)
            return self.attach_to_window_surface(
                surface,
                origin="auto",
                preferred_center_x=anchor_center_x,
            )
        self.refresh_movement_state()
        return True

    def has_vertical_edge_animation(self):
        return self.EDGE_INTERACTION_ENABLED and self.can_fly_freely()

    def get_edge_move_candidates(self):
        candidates = []
        for action_type in ["fly_up", "fly"]:
            if self.asset_manager.has_action("move", action_type):
                candidates.append(("move", action_type))
        return candidates

    def can_play_edge_move_animation(self):
        for purpose, action_type in self.get_edge_move_candidates():
            result = self.asset_manager.get_frames_for_action_by_score(
                purpose,
                action_type,
                self.mood_score,
                is_adult=self.is_adult,
                context="random",
            )
            if result:
                return True
        return False

    def get_edge_idle_candidates(self):
        candidates = []
        for action_type in ["side", "stand", "observe", "rest", "sit"]:
            if self.asset_manager.has_action("idle", action_type):
                candidates.append(("idle", action_type))
        return candidates or self.get_idle_candidates()

    def get_edge_vertical_speed(self, descending=False):
        base_speed = max(2.0, self.get_base_speed() + 0.3)
        if descending:
            base_speed += 0.4
        return max(1, int(round(base_speed)))

    def can_start_edge_mode(self, now=None):
        if not self.EDGE_INTERACTION_ENABLED:
            return False, "none"
        if now is None:
            now = app_now()
        if (
            self.edge_mode != "none" or
            self.dragging or
            self.vy != 0 or
            not self.isVisible() or
            self.state != "move" or
            self.care_mode != "none" or
            self.social_mode != "none" or
            self.is_recovering or
            self.is_under_care(now) or
            now < self.edge_cooldown_end
        ):
            return False, "none"
        if not self.has_vertical_edge_animation() or not self.can_play_edge_move_animation():
            return False, "none"
        side = self.get_edge_attach_target()
        return side != None, side or "none"

    def start_edge_mode(self, side, now=None):
        if now is None:
            now = app_now()
        if side not in {"left", "right"}:
            return False
        surface = self.get_surface_snapshot()
        available_height = surface.floor_top_y - surface.top_bound
        if available_height < 120:
            return False
        max_climb = max(80, min(available_height - 40, 360))
        min_climb = min(140, max_climb)
        climb_distance = random.randint(min_climb, max_climb)
        self.edge_mode = "climb_up"
        self.edge_side = side
        self.edge_target_y = max(surface.top_bound, surface.floor_top_y - climb_distance)
        self.edge_return_x = 0
        self.edge_pause_until = 0.0
        self.reset_stationary_move_mode()
        self.state = "move"
        self.direction = -1 if side == "left" else 1
        self.ensure_candidate_animation(self.get_edge_move_candidates(), context="random")
        self.refresh_movement_state()
        return True

    def stop_edge_mode(self, apply_cooldown=True):
        previous_side = self.edge_side
        was_active = self.edge_mode != "none"
        self.edge_mode = "none"
        self.edge_side = "none"
        self.edge_target_y = 0
        self.edge_return_x = 0
        self.edge_pause_until = 0.0
        if apply_cooldown and was_active:
            self.edge_cooldown_end = app_now() + random.uniform(8.0, 14.0)
        if previous_side == "left":
            self.direction = 1
        elif previous_side == "right":
            self.direction = -1
        self.state = "idle"
        self.state_timer = random.randint(60, 120)
        self.change_state("idle", "stand")
        self.refresh_movement_state()

    def try_start_edge_mode(self, now=None):
        can_start, side = self.can_start_edge_mode(now=now)
        if not can_start:
            return False
        chance = 0.24
        if random.random() >= chance:
            return False
        return self.start_edge_mode(side, now=now)

    def update_edge_behavior(self, now):
        if not self.EDGE_INTERACTION_ENABLED:
            if self.edge_mode != "none":
                self.stop_edge_mode(apply_cooldown=False)
            return False
        if self.edge_mode == "none":
            return False
        if (
            self.dragging or
            self.vy != 0 or
            self.care_mode != "none" or
            self.social_mode != "none" or
            self.is_recovering
        ):
            self.stop_edge_mode(apply_cooldown=False)
            return False

        surface = self.get_surface_snapshot()
        edge_x = surface.left_bound if self.edge_side == "left" else surface.right_bound
        self.direction = -1 if self.edge_side == "left" else 1

        if self.edge_mode == "climb_up":
            self.state = "move"
            self.ensure_candidate_animation(self.get_edge_move_candidates(), context="random")
            step = self.get_edge_vertical_speed(descending=False)
            next_y = max(self.edge_target_y, self.y() - step)
            self.move(edge_x, next_y)
            if next_y <= self.edge_target_y:
                self.edge_mode = "perch"
                self.edge_pause_until = now + random.uniform(0.8, 1.6)
            self.refresh_movement_state()
            return True

        if self.edge_mode == "perch":
            self.state = "idle"
            self.ensure_candidate_animation(self.get_edge_idle_candidates(), context="random")
            self.move(edge_x, self.y())
            if now >= self.edge_pause_until:
                inward = random.randint(90, 220)
                self.edge_return_x = surface.clamp_x(edge_x + inward if self.edge_side == "left" else edge_x - inward)
                self.edge_target_y = self.get_taskbar_walk_y()
                self.edge_mode = "return_taskbar"
            self.refresh_movement_state()
            return True

        if self.edge_mode == "climb_down":
            self.state = "move"
            self.ensure_candidate_animation(self.get_edge_move_candidates(), context="random")
            step = self.get_edge_vertical_speed(descending=True)
            next_y = min(surface.floor_top_y, self.y() + step)
            self.move(edge_x, next_y)
            if next_y >= surface.floor_top_y:
                self.move(edge_x, surface.floor_top_y)
                self.stop_edge_mode(apply_cooldown=True)
            else:
                self.refresh_movement_state()
            return True

        if self.edge_mode == "return_taskbar":
            self.state = "move"
            self.ensure_candidate_animation(self.get_edge_move_candidates(), context="random")
            self.direction = 1 if self.edge_return_x >= self.x() else -1
            arrived = self.move_flight_toward(
                self.edge_return_x,
                self.edge_target_y,
                speed=max(2.8, self.get_window_flight_speed()),
            )
            if arrived:
                self.move(self.edge_return_x, self.edge_target_y)
                self.stop_edge_mode(apply_cooldown=True)
            else:
                self.refresh_movement_state()
            return True

        self.stop_edge_mode(apply_cooldown=False)
        return False

    def is_distressed(self):
        if self.current_mood_tag in self.DISTRESS_MOODS:
            return True
        return self.mood_state == "depressed" and self.current_mood_tag not in {"happy", "smile", "confidence", "cool"}

    def is_under_care(self, now):
        return self.care_partner is not None and self.care_lock_mode != "none" and now < self.care_lock_end_time

    def clear_care_lock(self):
        if self.care_lock_mode == "hidden" and not self.isVisible():
            self.show()
        self.care_partner = None
        self.care_lock_mode = "none"
        self.care_lock_end_time = 0.0

    def get_care_release_padding(self):
        return 24

    def clamp_x_to_virtual_geometry(self, x, width, padding=0):
        vr = get_total_virtual_geometry()
        min_x = vr.left() + padding
        max_x = vr.right() - width - padding
        if max_x < min_x:
            min_x = vr.left()
            max_x = vr.right() - width
        return max(min_x, min(max_x, x))

    def get_child_release_position(self, child, direction=None, offset=None):
        if direction is None:
            direction = self.care_move_direction or self.direction or 1
        if offset is None:
            offset = random.randint(40, 60)
        adult_center_x = self.x() + (self.width() // 2)
        child_x = int(adult_center_x + (direction * offset) - (child.width() / 2))
        child_x = self.clamp_x_to_virtual_geometry(
            child_x,
            child.width(),
            padding=self.get_care_release_padding(),
        )
        screen = QApplication.screenAt(self.geometry().center()) or QApplication.primaryScreen()
        geom = screen.availableGeometry()
        child_y = geom.bottom() - child.height()
        return child_x, child_y

    def should_finish_moving_interaction_at_edge(self, child, step):
        direction = self.care_move_direction or self.direction or 1
        vr = get_total_virtual_geometry()
        projected_x = self.x() + (step * direction)
        if projected_x < vr.left() or projected_x + self.width() > vr.right():
            return True
        projected_center_x = projected_x + (self.width() // 2)
        projected_child_x = int(projected_center_x + (direction * 60) - (child.width() / 2))
        clamped_child_x = self.clamp_x_to_virtual_geometry(
            projected_child_x,
            child.width(),
            padding=self.get_care_release_padding(),
        )
        return projected_child_x != clamped_child_x

    def release_hidden_child_nearby(self, child):
        child_x, child_y = self.get_child_release_position(child)
        child.move(child_x, child_y)

    def should_ignore_collision(self):
        now = app_now()
        return (
            self.dragging or
            self.vy != 0 or
            not self.isVisible() or
            self.flight_mode != "none" or
            self.perched_window_hwnd != 0 or
            self.edge_mode != "none" or
            self.is_hugging or
            self.care_mode != "none" or
            self.care_partner is not None or
            self.is_under_care(now)
        )

    def apply_animation_result(self, purpose, result):
        if not result:
            return False
        frames, action_type, mood = result
        if not frames:
            return False
        self.current_frames = frames
        self.frame_index = 0
        self.current_purpose = purpose
        self.current_action_tag = action_type
        self.current_mood_tag = mood
        return True

    def change_state_candidates(self, candidates, context=None):
        for purpose, action_type in candidates:
            result = self.asset_manager.get_frames_for_action_by_score(
                purpose,
                action_type,
                self.mood_score,
                is_adult=self.is_adult,
                context=context,
            )
            if self.apply_animation_result(purpose, result):
                return True
        return False

    def change_state_candidates_with_preferences(self, candidates, preferred_moods, forbidden=None, context=None):
        for mood_tag in preferred_moods:
            for purpose, action_type in candidates:
                frames = self.asset_manager.get_specific_frames(
                    purpose,
                    action_type,
                    mood_tag,
                    mood_score=self.mood_score,
                    context=context,
                )
                if frames and self.apply_animation_result(purpose, (frames, action_type, mood_tag)):
                    return True
        for purpose, action_type in candidates:
            result = self.asset_manager.get_frames_for_action_by_preferences(
                purpose,
                action_type,
                preferred_moods,
                forbidden=forbidden,
                mood_score=self.mood_score,
                context=context,
            )
            if self.apply_animation_result(purpose, result):
                return True
        return False

    def get_severe_moods(self):
        return self.ADULT_SEVERE_MOODS if self.is_adult else self.SEVERE_MOODS

    def get_speed_for_mood_score(self, mood_score):
        if mood_score < 20:
            return 1.1 + (mood_score / 20.0) * 0.6
        if mood_score < 50:
            return 1.5 + ((mood_score - 20.0) / 30.0) * 0.9
        return 0.4 + (mood_score / 100.0) * 2.6

    def get_base_speed(self):
        return self.get_speed_for_mood_score(self.mood_score)

    def get_distressed_move_speed(self):
        return self.get_speed_for_mood_score(35.0)

    def get_care_approach_speed(self):
        return max(2.8, self.get_base_speed() + 0.6)

    def reset_stationary_move_mode(self):
        self.stationary_move_mode = False
        self.stationary_move_key = ""

    def is_stationary_move_candidate(self):
        return (
            self.name == "Tokai Teio" and
            self.current_purpose == "move" and
            self.current_action_tag in {"jog", "walk_drink"}
        )

    def configure_stationary_move_mode(self, context="random", force=False):
        if context != "random" or not self.is_stationary_move_candidate():
            self.reset_stationary_move_mode()
            return
        current_key = f"{context}:{self.current_action_tag}"
        if not force and self.stationary_move_key == current_key:
            return
        self.stationary_move_key = current_key
        stationary_chances = {
            "jog": 0.35,
            "walk_drink": 0.65,
        }
        self.stationary_move_mode = random.random() < stationary_chances.get(self.current_action_tag, 0.0)

    def expand_candidates_with_context(self, purpose, candidates, context=None):
        expanded = list(candidates)
        seen = set(expanded)
        extra_actions = self.asset_manager.get_action_keys_for_context(
            purpose,
            mood_score=self.mood_score,
            context=context,
        )
        for action_type in extra_actions:
            candidate = (purpose, action_type)
            if candidate not in seen:
                expanded.append(candidate)
                seen.add(candidate)
        return expanded

    def ensure_candidate_animation(self, candidates, context=None):
        if any(self.current_purpose == purpose and self.current_action_tag == action for purpose, action in candidates):
            frames = self.asset_manager.get_specific_frames(
                self.current_purpose,
                self.current_action_tag,
                self.current_mood_tag,
                mood_score=self.mood_score,
                context=context,
            )
            if frames:
                return True
        return self.change_state_candidates(candidates, context=context)

    def ensure_candidate_animation_with_preferences(self, candidates, preferred_moods, forbidden=None, context=None):
        if any(self.current_purpose == purpose and self.current_action_tag == action for purpose, action in candidates):
            frames = self.asset_manager.get_specific_frames(
                self.current_purpose,
                self.current_action_tag,
                self.current_mood_tag,
                mood_score=self.mood_score,
                context=context,
            )
            if self.current_mood_tag in preferred_moods and frames:
                return True
        return self.change_state_candidates_with_preferences(
            candidates,
            preferred_moods,
            forbidden=forbidden,
            context=context,
        )

    def get_child_comfort_candidates(self):
        if self.name == "Tokai Teio":
            return [
                ("idle", "drink"),
                ("idle", "eat"),
                ("idle", "side_eat_candy"),
                ("idle", "sit"),
                ("idle", "lie"),
                ("idle", "side"),
                ("idle", "side_hug"),
            ]
        return [
            ("idle", "drink"),
            ("idle", "eat"),
            ("idle", "side_hug"),
            ("idle", "side_rub"),
            ("idle", "sit_no"),
            ("idle", "squat"),
            ("idle", "side"),
        ]

    def get_child_recovery_candidates(self):
        if self.name == "Tokai Teio":
            return [
                ("move", "walk_drink"),
                ("idle", "dance_uma_drink"),
                ("idle", "side_eat_candy"),
                ("idle", "lie"),
                ("idle", "side"),
                ("idle", "sit"),
            ]
        return self.get_child_comfort_candidates()

    def get_adult_companion_candidates(self):
        return [
            ("idle", "sit"),
            ("idle", "sit_talk"),
            ("idle", "sit_read"),
            ("idle", "rest"),
            ("idle", "squat"),
            ("idle", "side"),
        ]

    def get_move_candidates(self):
        return [
            ("move", "walk"),
            ("move", "run"),
            ("move", "jog"),
            ("move", "sneak"),
            ("move", "climb"),
            ("move", "fly"),
            ("move", "fly_up"),
        ]

    def get_care_move_candidates(self):
        return [
            ("move", "run"),
            ("move", "jog"),
            ("move", "walk"),
            ("move", "sneak"),
            ("move", "climb"),
            ("move", "fly"),
            ("move", "fly_up"),
        ]

    def get_idle_candidates(self):
        return [
            ("idle", "stand"),
            ("idle", "side"),
            ("idle", "sit"),
            ("idle", "rest"),
            ("idle", "lie"),
            ("idle", "squat"),
            ("idle", "observe"),
            ("idle", "photo"),
            ("idle", "photo_ready"),
            ("idle", "dance_three"),
            ("idle", "dance_uma"),
            ("idle", "hear"),
            ("idle", "knock"),
            ("idle", "get"),
            ("idle", "sleep"),
        ]

    def get_randomized_candidates(self, candidates):
        randomized = list(candidates)
        random.shuffle(randomized)
        return randomized

    def start_recovery(self, now):
        self.stop_social_mode(now, apply_cooldown=False)
        self.is_recovering = True
        self.recovery_end_time = now + 8.0
        self.recovery_motion_mode = "stay"
        self.reset_stationary_move_mode()
        self.clear_care_lock()
        self.state = "idle"
        recovery_candidates = self.get_randomized_candidates(self.get_child_recovery_candidates())
        if not self.change_state_candidates(recovery_candidates):
            self.change_state("idle", "stand")
        elif self.current_purpose == "move":
            if self.name == "Tokai Teio" and random.random() < 0.4:
                self.recovery_motion_mode = "walk"
                self.state = "move"

    def maintain_care_lock(self, now):
        if self.care_partner and self.social_mode != "none":
            self.stop_social_mode(now, apply_cooldown=False)
        if self.care_partner and self.care_lock_mode == "none":
            self.state = "idle"
            return True
        if not self.is_under_care(now):
            self.clear_care_lock()
            return False
        if self.care_lock_mode == "hidden":
            if self.isVisible():
                self.hide()
            return True
        if not self.isVisible():
            self.show()
        if self.care_partner:
            self.direction = -1 if self.care_partner.x() < self.x() else 1
        self.state = "idle"
        self.ensure_candidate_animation(self.get_child_comfort_candidates())
        self.mood_score = min(100, self.mood_score + 0.05)
        return True

    def paintEvent(self, event):
        if not self.current_frames: return
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pixmap = self.current_frames[self.frame_index]
        draw_x = (self.width() - pixmap.width()) // 2
        draw_y = self.height() - pixmap.height()
        overlay_scale = max(1.0, math.sqrt(self.display_scale_multiplier))
        painter.save()
        should_flip = (self.direction == 1) if self.original_face_left else (self.direction == -1)
        if should_flip:
            painter.translate(self.width(), 0); painter.scale(-1, 1)
            painter.drawPixmap(self.width() - draw_x - pixmap.width(), draw_y, pixmap)
        else:
            painter.drawPixmap(draw_x, draw_y, pixmap)
        painter.restore()

        if self.bar_opacity > 0:
            painter.setOpacity(self.bar_opacity)
            bar_w, bar_h = 60, 5
            bar_x, bar_y = (self.width() - bar_w) // 2, draw_y - 12
            painter.setBrush(QColor(0, 0, 0, 120)); painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 2, 2)
            color = QColor(255, 50, 50) if self.mood_score < 20 else QColor(255, 200, 50) if self.mood_score < 50 else QColor(80, 255, 80)
            painter.setBrush(color)
            painter.drawRoundedRect(bar_x, bar_y, int(bar_w * (self.mood_score / 100)), bar_h, 2, 2)

        if self.show_heart and not self.heart_pixmap.isNull():
            painter.setOpacity(self.heart_opacity)
            h_s = int(35 * overlay_scale)
            painter.drawPixmap((self.width() - h_s) // 2, draw_y - 20 - self.heart_y_offset, h_s, h_s, self.heart_pixmap)

        # --- 星星繪製 (修正位置：正確放在馬娘身上) ---
        if self.star_opacity > 0 and not self.star_pixmap.isNull():
            painter.setOpacity(self.star_opacity)
            s_size, spacing, num_stars = int(25 * overlay_scale), int(30 * overlay_scale), 3
            start_x = (self.width() - (num_stars * s_size)) // 2
            star_base_y = draw_y - 50 + self.star_y_offset
            for i in range(num_stars):
                individual_offset = int(math.sin((self.star_anim_counter + i * 20) * 0.1) * 3)
                painter.drawPixmap(start_x + i * spacing, star_base_y + individual_offset, s_size, s_size, self.star_pixmap)
        painter.setOpacity(1.0)

    def next_frame(self):
        if self.current_frames: self.frame_index = (self.frame_index + 1) % len(self.current_frames); self.update()

    def update_mood(self, all_pets):
        nearby = []
        my_center = self.geometry().center()
        for other in all_pets:
            if other == self or not other.isVisible(): continue
            if math.hypot(my_center.x() - other.geometry().center().x(), my_center.y() - other.geometry().center().y()) < 250: nearby.append(other)
        rec = 0.5 + (0.5 if not self.is_adult else 0.0)
        if nearby:
            rec += 0.5
            if not self.is_adult and any(p.is_adult for p in nearby): rec += 2.0
        if not self.is_adult:
            if not nearby:
                self.lonely_timer += 3
                if self.lonely_timer >= 10: rec -= 2.0
            else: self.lonely_timer = 0
        self.mood_score = max(0, min(100, self.mood_score + rec + random.uniform(-1, 1)))
        old_s = self.mood_state
        self.mood_state = "depressed" if self.mood_score < 20 else "unhappy" if self.mood_score < 50 else "normal"
        if old_s != self.mood_state:
            target_purpose = self.current_purpose or ("move" if self.state == "move" else "idle")
            self.change_state(target_purpose, self.current_action_tag)

    def tick(self, all_pets):
        if not self.dragging:
            if self.update_window_perch(all_pets):
                return
            if self.update_window_flight():
                return
            now = app_now()
            if self.update_edge_behavior(now):
                return
            self.apply_gravity()
            self.check_boundary_stuck()
            self.refresh_movement_state()
            if self.vy == 0: self.update_ai_behavior(all_pets)

    def apply_gravity(self):
        surface = self.get_surface_snapshot()
        floor_top_y = surface.floor_top_y
        if self.vy != 0 or self.y() < floor_top_y:
            self.vy += self.gravity
            next_y = self.y() + int(self.vy)
            if next_y >= floor_top_y:
                imp = self.vy
                self.move(self.x(), floor_top_y)
                if abs(imp) > 15:
                    self.mood_score -= 15
                    self.apply_reaction(["scared", "exhausted", "cry"], is_negative=True)
                    self.vy = imp * self.bounce
                elif abs(imp) > 3:
                    self.vy *= -0.4
                else:
                    self.vy = 0
            else:
                self.move(self.x(), next_y)
        elif self.y() > floor_top_y:
            self.move(self.x(), floor_top_y)
            self.vy = 0
        self.refresh_movement_state()

    def update_star_animation(self):
        target_opacity = 1.0 if self.social_mode in ["following", "mimicking"] else 0.0
        if self.star_opacity < target_opacity: self.star_opacity = min(1.0, self.star_opacity + 0.1)
        elif self.star_opacity > target_opacity: self.star_opacity = max(0.0, self.star_opacity - 0.1)
        self.star_anim_counter = (self.star_anim_counter + 1) % 360
        self.star_y_offset = int(math.sin(self.star_anim_counter * 0.1) * 5)
        if self.star_opacity > 0: self.update()
        else: self.star_timer.stop()

    def start_social_mode(self, mode, target, now):
        self.social_mode = mode
        self.social_target = target
        self.social_started_at = now
        self.social_timer_frames = self.get_social_duration_frames(mode)
        self.star_timer.start(30)

    def stop_social_mode(self, now, apply_cooldown=True):
        if apply_cooldown and self.social_mode != "none":
            self.social_cooldown_end = now + self.get_social_cooldown_seconds()
        self.social_mode = "none"
        self.social_target = None
        self.social_started_at = 0.0
        self.social_timer_frames = 0

    def can_strictly_mimic(self, target):
        return bool(self.asset_manager.get_specific_frames(
            target.current_purpose,
            target.current_action_tag,
            target.current_mood_tag,
        ))

    def sync_mimic_animation(self, target):
        frames = self.asset_manager.get_specific_frames(
            target.current_purpose,
            target.current_action_tag,
            target.current_mood_tag,
        )
        if not frames:
            return False
        if (
            self.current_purpose != target.current_purpose or
            self.current_action_tag != target.current_action_tag or
            self.current_mood_tag != target.current_mood_tag
        ):
            self.current_frames = frames
            self.frame_index = 0
            self.current_purpose = target.current_purpose
            self.current_action_tag = target.current_action_tag
            self.current_mood_tag = target.current_mood_tag
        return True

    def parse_interaction_action(self, action_key):
        if action_key.startswith("move_"):
            motion = "move"
            rest = action_key[len("move_"):]
        elif action_key.startswith("idle_"):
            motion = "idle"
            rest = action_key[len("idle_"):]
        else:
            return None
        if "_" not in rest:
            return None
        action_desc, child_token = rest.rsplit("_", 1)
        return motion, action_desc, child_token

    def get_distress_mood_candidates(self, child):
        moods = []
        for mood in [child.current_mood_tag, "sad", "cry", "hard-cry", "happy"]:
            if mood and mood not in moods:
                moods.append(mood)
        return moods

    def select_interaction_animation(self, child):
        child_tokens = set(child.get_child_tokens())
        actions = self.asset_manager.get_action_keys("interaction")
        if not actions:
            return None

        preferred_motion = "move" if self.state == "move" else "idle"
        motion_order = [preferred_motion, "idle" if preferred_motion == "move" else "move"]
        for motion in motion_order:
            for mood in self.get_distress_mood_candidates(child):
                matches = []
                for action_key in actions:
                    parsed = self.parse_interaction_action(action_key)
                    if not parsed:
                        continue
                    action_motion, _, child_token = parsed
                    if action_motion != motion or child_token not in child_tokens:
                        continue
                    interaction_context = "moving_interaction" if action_motion == "move" else "interaction"
                    frames = self.asset_manager.get_specific_frames(
                        "interaction",
                        action_key,
                        mood,
                        mood_score=child.mood_score,
                        context=interaction_context,
                    )
                    if frames:
                        matches.append((action_key, mood, frames))
                if matches:
                    return random.choice(matches)
        return None

    def start_care_approach(self, child):
        self.stop_social_mode(app_now(), apply_cooldown=False)
        self.care_mode = "approach"
        self.care_target = child
        self.care_plan = "auto"
        child.care_partner = self

    def decide_care_plan(self, child, has_interaction):
        if not has_interaction:
            return "companion"
        interaction_weights = {
            "Symboli Rudolf": 0.65,
            "Sirius Symboli": 0.50,
            "Air Groove": 0.40,
        }
        interaction_chance = interaction_weights.get(self.name, 0.50)
        if random.random() < interaction_chance:
            return "interaction"
        return "companion"

    def begin_hidden_interaction(self, child, animation_spec, now):
        action_key, mood, frames = animation_spec
        parsed = self.parse_interaction_action(action_key)
        motion = parsed[0] if parsed else "idle"
        self.care_mode = "moving_interaction" if motion == "move" else "interaction"
        self.care_end_time = now + 3.0
        self.is_hugging = True
        self.care_move_direction = self.direction or 1
        child.care_partner = self
        child.care_lock_mode = "hidden"
        child.care_lock_end_time = self.care_end_time
        child.hide()
        self.current_frames = frames
        self.frame_index = 0
        self.current_purpose = "interaction"
        self.current_action_tag = action_key
        self.current_mood_tag = mood
        self.state = "move" if self.care_mode == "moving_interaction" else "idle"

    def begin_companion_care(self, child, now):
        self.care_mode = "sit"
        self.care_end_time = now + 5.0
        child.care_partner = self
        child.care_lock_mode = "comfort"
        child.care_lock_end_time = self.care_end_time
        child.show()
        self.state = "idle"
        self.ensure_candidate_animation(self.get_adult_companion_candidates())
        child.state = "idle"
        child.ensure_candidate_animation(child.get_child_comfort_candidates())

    def finish_care_mode(self, success=True):
        now = app_now()
        child = self.care_target
        previous_mode = self.care_mode
        if child:
            if previous_mode == "moving_interaction":
                self.release_hidden_child_nearby(child)
            if not child.isVisible():
                child.show()
            child.clear_care_lock()
            if success:
                child.mood_score = min(100, child.mood_score + 25)
                child.pop_heart()
                child.start_recovery(now)
        self.is_hugging = False
        self.care_mode = "none"
        self.care_target = None
        self.care_end_time = 0.0
        self.care_move_direction = 0
        self.care_plan = "auto"
        self.care_cooldown_end = now + 4.0
        self.state = "idle"
        self.change_state("idle", "stand")

    def cancel_care_mode(self):
        child = self.care_target
        if child:
            if self.care_mode == "moving_interaction":
                self.release_hidden_child_nearby(child)
            if not child.isVisible():
                child.show()
            child.clear_care_lock()
        self.is_hugging = False
        self.care_mode = "none"
        self.care_target = None
        self.care_end_time = 0.0
        self.care_move_direction = 0
        self.care_plan = "auto"

    def move_toward_x(self, target_x, speed_scale=1.0, min_speed=None):
        delta = target_x - self.x()
        if abs(delta) <= 4:
            return True

        self.direction = 1 if delta > 0 else -1
        base_speed = self.get_base_speed()
        if min_speed is not None:
            base_speed = max(base_speed, min_speed)
        step = max(1, int(base_speed * speed_scale))
        nx = self.x() + (step * self.direction)
        surface = self.get_surface_snapshot()
        nx = surface.clamp_x(nx)
        if nx <= surface.left_bound:
            self.direction = 1
        elif nx >= surface.right_bound:
            self.direction = -1
        self.move(nx, self.y())
        self.refresh_movement_state()
        return abs(target_x - self.x()) <= step

    def update_care_behavior(self, now, all_pets):
        if not self.is_adult or not self.isVisible():
            if self.care_mode != "none":
                self.cancel_care_mode()
            return False

        care_enabled = self.dashboard.care_feature_enabled if self.dashboard else True
        if not care_enabled:
            if self.care_mode != "none":
                self.cancel_care_mode()
            return False

        if self.care_mode != "none":
            child = self.care_target
            if (
                not child or
                child not in all_pets or
                child.care_partner not in (None, self) or
                (not child.isVisible() and self.care_mode not in {"interaction", "moving_interaction"})
            ):
                self.cancel_care_mode()
                return False

            if self.care_mode == "interaction":
                if now >= self.care_end_time:
                    self.finish_care_mode(success=True)
                else:
                    child.mood_score = min(100, child.mood_score + 0.18)
                return True

            if self.care_mode == "moving_interaction":
                self.direction = self.care_move_direction or self.direction or 1
                self.state = "move"
                child.mood_score = min(100, child.mood_score + 0.18)
                step = max(1, int(round(self.get_distressed_move_speed())))
                if now >= self.care_end_time or self.should_finish_moving_interaction_at_edge(child, step):
                    self.finish_care_mode(success=True)
                else:
                    self.move(self.x() + (step * self.direction), self.y())
                return True

            if self.care_mode == "sit":
                self.direction = -1 if child.x() < self.x() else 1
                child.direction = -1 if self.x() < child.x() else 1
                self.ensure_candidate_animation(self.get_adult_companion_candidates())
                child.ensure_candidate_animation(child.get_child_comfort_candidates())
                child.mood_score = min(100, child.mood_score + 0.10)
                if now >= self.care_end_time or child.mood_score >= 70:
                    self.finish_care_mode(success=True)
                return True

            if not child.is_distressed() and child.mood_score >= 55:
                self.finish_care_mode(success=False)
                return False

            interaction_spec = self.select_interaction_animation(child)
            if self.care_plan == "auto":
                self.care_plan = self.decide_care_plan(child, interaction_spec is not None)
            elif self.care_plan == "interaction" and not interaction_spec:
                self.care_plan = "companion"

            use_interaction = self.care_plan == "interaction" and interaction_spec is not None
            offset = 120 if self.x() <= child.x() else -120
            target_x = child.x() if use_interaction else child.x() - offset
            self.state = "move"
            self.ensure_candidate_animation_with_preferences(
                self.expand_candidates_with_context("move", self.get_care_move_candidates(), context="care_approach"),
                ["hurry", "cool", "effort", "confidence", "smile", "happy"],
                forbidden=["cry", "hard-cry", "scared"],
                context="care_approach",
            )
            arrived = self.move_toward_x(
                target_x,
                speed_scale=1.6,
                min_speed=self.get_care_approach_speed(),
            )
            if arrived or self.distance_to(child) < 140:
                if use_interaction:
                    self.begin_hidden_interaction(child, interaction_spec, now)
                else:
                    self.begin_companion_care(child, now)
            return True

        if now < self.care_cooldown_end:
            return False

        radius = None if self.name == "Sirius Symboli" else 1000
        candidates = []
        for pet in all_pets:
            if pet == self or pet.is_adult or not pet.isVisible():
                continue
            if pet.care_partner not in (None, self):
                continue
            if pet.is_recovering or not pet.is_distressed():
                continue
            dist = self.distance_to(pet)
            if radius is not None and dist > radius:
                continue
            candidates.append((dist, pet))

        if not candidates:
            return False

        candidates.sort(key=lambda item: item[0])
        self.start_care_approach(candidates[0][1])
        return True

    def update_social_behavior(self, now, all_pets):
        if self.name not in self.CHILD_NAMES or self.dragging:
            return False

        rudolf = next((p for p in all_pets if p.name == "Symboli Rudolf" and p.isVisible()), None)
        if self.social_mode != "none":
            if not rudolf or self.social_target != rudolf:
                self.stop_social_mode(now)
                return False

            dist = self.distance_to(rudolf)
            self.social_timer_frames -= 1
            timed_out = self.social_timer_frames <= 0
            if timed_out or dist > (self.social_distance + 150):
                self.stop_social_mode(now)
                return False

            if self.social_mode == "following":
                if rudolf.current_purpose != "move":
                    self.stop_social_mode(now)
                    return False
                self.state = "move"
                follow_x = rudolf.x() + (rudolf.direction * 120)
                self.move_toward_x(follow_x, speed_scale=1.25)
                self.ensure_candidate_animation(self.get_move_candidates())
                return True

            if self.social_mode == "mimicking":
                if not self.sync_mimic_animation(rudolf):
                    self.stop_social_mode(now)
                    return False
                self.direction = rudolf.direction
                self.state = "move" if rudolf.current_purpose == "move" else "idle"
                if rudolf.current_purpose == "move":
                    self.move_toward_x(rudolf.x(), speed_scale=1.05)
                return True

        if not rudolf or now < self.social_cooldown_end:
            return False

        dist = self.distance_to(rudolf)
        is_behind = (self.x() - rudolf.x()) * rudolf.direction < 0
        if dist >= self.social_distance:
            return False

        if rudolf.current_purpose == "move" and is_behind:
            self.start_social_mode("following", rudolf, now)
            return True

        if self.can_strictly_mimic(rudolf):
            self.start_social_mode("mimicking", rudolf, now)
            return True

        return False

    def update_random_behavior(self):
        if self.mood_score < 20 and self.current_purpose != "interaction":
            self.last_x = self.x()
            self.state_timer -= 1
            if self.current_mood_tag not in self.get_severe_moods() or self.state_timer <= 0:
                self.state = random.choice(["idle", "move"])
                self.state_timer = random.randint(60, 110)
                self.current_purpose = ""
                self.reset_stationary_move_mode()
                if random.random() < 0.25:
                    self.direction *= -1

            severe_candidates = self.expand_candidates_with_context(
                "move" if self.state == "move" else "idle",
                self.get_move_candidates() if self.state == "move" else self.get_idle_candidates(),
                context="random",
            )
            if self.current_purpose != ("move" if self.state == "move" else "idle"):
                if self.change_state_candidates(self.get_randomized_candidates(severe_candidates), context="random"):
                    self.configure_stationary_move_mode("random", force=True)

            if self.state == "move":
                if self.try_start_window_flight(app_now()):
                    return
                if self.try_start_edge_mode(app_now()):
                    return
                if not self.stationary_move_mode:
                    self.move_logic()
                if self.current_purpose != "move":
                    if self.change_state_candidates(
                        self.get_randomized_candidates(
                            self.expand_candidates_with_context("move", self.get_move_candidates(), context="random")
                        ),
                        context="random",
                    ):
                        self.configure_stationary_move_mode("random", force=True)
            else:
                self.reset_stationary_move_mode()
                if self.current_purpose != "idle":
                    if self.change_state_candidates(
                        self.get_randomized_candidates(
                            self.expand_candidates_with_context("idle", self.get_idle_candidates(), context="random")
                        ),
                        context="random",
                    ):
                        self.reset_stationary_move_mode()
            return

        if self.state == "move":
            if self.try_start_window_flight(app_now()):
                return
            if self.try_start_edge_mode(app_now()):
                return
            if self.stationary_move_mode:
                self.stuck_count = 0
            elif abs(self.x() - self.last_x) < 0.5:
                self.stuck_count += 1
            else:
                self.stuck_count = max(0, self.stuck_count - 1)
            if self.stuck_count > 60:
                self.direction *= -1
                self.state_timer = random.randint(30, 80)
                self.stuck_count = 0

        self.last_x = self.x()
        self.state_timer -= 1
        if self.state_timer <= 0:
            self.state = random.choice(["idle", "move"])
            self.state_timer = random.randint(100, 150)
            self.current_purpose = ""
            self.reset_stationary_move_mode()
            if random.random() < 0.3:
                self.direction *= -1

        base_speed = self.get_base_speed()
        visual_p = "move" if (self.state == "move" and base_speed > 0.8) else "idle"
        if self.current_purpose != visual_p:
            candidates = self.expand_candidates_with_context(
                visual_p,
                self.get_move_candidates() if visual_p == "move" else self.get_idle_candidates(),
                context="random",
            )
            if self.change_state_candidates(self.get_randomized_candidates(candidates), context="random"):
                self.configure_stationary_move_mode("random", force=True)

        if self.state == "move":
            if not self.stationary_move_mode:
                self.move_logic()
            if self.current_purpose != "move":
                if self.change_state_candidates(
                    self.get_randomized_candidates(
                        self.expand_candidates_with_context("move", self.get_move_candidates(), context="random")
                    ),
                    context="random",
                ):
                    self.configure_stationary_move_mode("random", force=True)
        else:
            self.reset_stationary_move_mode()
            if self.current_purpose != "idle":
                if self.change_state_candidates(
                    self.get_randomized_candidates(
                        self.expand_candidates_with_context("idle", self.get_idle_candidates(), context="random")
                    ),
                    context="random",
                ):
                    self.reset_stationary_move_mode()

    def update_ai_behavior(self, all_pets):
        now = app_now()
        if self.is_angry_locked:
            self.refresh_movement_state()
            return

        if self.is_recovering:
            if now > self.recovery_end_time:
                self.is_recovering = False
                self.recovery_motion_mode = "stay"
                self.reset_stationary_move_mode()
                self.change_state("idle", "stand")
            else:
                if self.recovery_motion_mode == "walk" and self.current_purpose == "move":
                    self.move_logic()
                self.refresh_movement_state()
                return

        if self.maintain_care_lock(now):
            self.refresh_movement_state()
            return

        if self.update_care_behavior(now, all_pets):
            self.refresh_movement_state()
            return

        if self.update_social_behavior(now, all_pets):
            self.refresh_movement_state()
            return

        self.update_random_behavior()
        self.refresh_movement_state()

    def move_logic(self):
        base_speed = self.get_base_speed()
        nx = self.x() + int(base_speed * self.direction)
        surface = self.get_surface_snapshot()
        clamped_x = surface.clamp_x(nx)
        if clamped_x != nx:
            self.direction *= -1
        else:
            self.move(clamped_x, self.y())
        self.refresh_movement_state()

    def check_boundary_stuck(self):
        surface = self.get_surface_snapshot()
        if self.x() < surface.left_bound:
            self.move(surface.left_bound + 5, self.y())
            self.direction = 1
        elif self.x() > surface.right_bound:
            self.move(surface.right_bound - 5, self.y())
            self.direction = -1
        self.refresh_movement_state()

    def apply_reaction(self, p_list, is_negative=False):
        forbidden = ["happy", "smile", "confidence", "cool", "glance"] if is_negative else []
        result = self.asset_manager.get_safe_reaction_result("idle", p_list, forbidden=forbidden)
        if self.apply_animation_result("idle", result):
            self.state = "idle"
            self.state_timer = 80
            self.reset_stationary_move_mode()

    def change_state(self, p, a=None):
        result = self.asset_manager.get_frames_by_score(p, a, self.mood_score, is_adult=self.is_adult)
        self.apply_animation_result(p, result)

    def resolve_collision(self, all_pets):
        if self.should_ignore_collision():
            return
        my_c = self.geometry().center(); repel_x = 0.0; repel_weight = 0.2 if self.mood_score >= 20 else 0.05
        for other in all_pets:
            if other == self or other.should_ignore_collision(): continue
            dist_v = my_c - other.geometry().center(); dist = math.hypot(dist_v.x(), dist_v.y())
            eff_rad = self.radius + other.radius
            if dist < eff_rad:
                overlap = eff_rad - dist
                if overlap > 5.0:
                    total_mass = self.mass + other.mass
                    repel_x += (dist_v.x() / (dist if dist > 0 else 1)) * overlap * (other.mass / total_mass)
                    if not self.is_adult and other.is_adult: other.mood_score = min(100, other.mood_score + 0.01)
        if abs(repel_x) > 0.5: self.move(self.x() + int(repel_x * repel_weight), self.y())

    def trigger_care_event(self, child):
        spec = self.select_interaction_animation(child)
        if spec:
            self.begin_hidden_interaction(child, spec, app_now())
        else:
            self.begin_companion_care(child, app_now())

    def finish_care(self, child=None):
        self.finish_care_mode(success=True)

    def enterEvent(self, event): self.fade_anim.setStartValue(self.bar_opacity); self.fade_anim.setEndValue(1.0); self.fade_anim.start()
    def leaveEvent(self, event): self.fade_anim.setStartValue(self.bar_opacity); self.fade_anim.setEndValue(0.0); self.fade_anim.start()
    def mousePressEvent(self, event):
        if self.is_angry_locked or self.care_mode != "none" or self.is_under_care(app_now()): return
        if event.button() == Qt.MouseButton.LeftButton:
            if self.flight_mode != "none":
                self.stop_window_flight(apply_cooldown=False)
            if self.edge_mode != "none":
                self.stop_edge_mode(apply_cooldown=False)
            self.dragging, self.vy, self.drag_start_time = True, 0, time.time()
            self.drag_pos = event.globalPosition().toPoint() - self.pos()
            self.apply_drag_animation()
            self.refresh_movement_state()
    def mouseMoveEvent(self, event):
        if self.dragging:
            if self.perched_window_hwnd:
                self.detach_from_window_surface()
            target_pos = event.globalPosition().toPoint() - self.drag_pos
            clamped_x, clamped_y = DesktopGeometry.clamp_drag_position(self, target_pos.x(), target_pos.y())
            self.move(clamped_x, clamped_y)
            self.refresh_movement_state()
    def mouseReleaseEvent(self, event):
        if self.is_angry_locked or self.care_mode != "none" or self.is_under_care(app_now()): return
        if event.button() == Qt.MouseButton.LeftButton:
            dur, self.dragging = time.time() - self.drag_start_time, False
            if dur >= 0.2 and self.try_snap_to_window_surface():
                self.refresh_movement_state()
                return
            if dur < 0.2:
                self.click_count += 1; self.click_reset_timer.start(3000); self.state, self.state_timer = "idle", 100
                if self.click_count >= 5:
                    self.is_angry_locked, self.mood_score = True, max(0, self.mood_score - 60)
                    self.setCursor(Qt.CursorShape.ForbiddenCursor); self.apply_reaction(["scold", "angry"], is_negative=True); self.lock_timer.start(5000)
                else: self.mood_score = min(100, self.mood_score + 8); self.pop_heart(); self.apply_reaction(["happy", "smile"])
            elif dur > 5.0:
                self.mood_score = max(0, self.mood_score - 25); self.apply_reaction(["scold", "hard-cry", "exhausted"], is_negative=True)
            else:
                self.change_state("idle")
            self.refresh_movement_state()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    config_store = ConfigStore()
    window_tracker = WindowTracker()

    assets_dir = AssetManager.get_resource_path("assets_cropped")
    if not os.path.exists(assets_dir): sys.exit()

    configs = [
        ("Symboli Rudolf", 0.45, "滷豆腐"),
        ("Tokai Teio", 0.35, "帝寶"),
        ("Sirius Symboli", 0.4, "天狼星"),
        ("Tsurumaru Tsuyoshi", 0.3, "鶴寶"),
        ("Air Groove", 0.4, "氣槽")
    ]

    pets_dict, pets_list = {}, []
    # 1. 建立寵物
    for i, (fn, sc, dn) in enumerate(configs):
        path = os.path.join(assets_dir, fn)
        if os.path.exists(path):
            p = TanukiPet(fn, path, sc)
            p.move(500 + i * 100, 600)
            if fn != "Symboli Rudolf":
                p.user_visible = False
                p.hide()
            pets_dict[fn] = {"pet": p, "name": dn}
            pets_list.append(p)

    # 2. 建立面板
    l_screen = min(QApplication.screens(), key=lambda s: s.geometry().x())
    av_rect = l_screen.availableGeometry()
    dash = Dashboard(av_rect, pets_dict)

    # 3. 重要：將 dash 實體回填給所有寵物，防止閃退
    for p in pets_list:
        p.dashboard = dash
        p.window_tracker = window_tracker
    config_store.bind(dash, pets_dict)
    window_tracker.refresh()

    # 4. 其他組件
    sensor = SensorZone(dash)
    sensor.setGeometry(av_rect.left(), av_rect.bottom() - 300, 20, 300)
    monitor = GlobalMouseListener(dash)

    # 5. 計時器設定
    mood_t = QTimer();
    mood_t.timeout.connect(lambda: [p.update_mood(pets_list) for p in pets_list]);
    mood_t.start(3000)
    SIM_CLOCK.register_timer(mood_t, 3000)
    phys_t = QTimer();
    phys_t.timeout.connect(lambda: [p.resolve_collision(pets_list) for p in pets_list]);
    phys_t.start(30)
    SIM_CLOCK.register_timer(phys_t, 30)
    logic_t = QTimer();
    logic_t.timeout.connect(lambda: [p.tick(pets_list) for p in pets_list]);
    logic_t.start(30)
    SIM_CLOCK.register_timer(logic_t, 30)
    window_t = QTimer();
    window_t.timeout.connect(window_tracker.refresh);
    window_t.start(150)
    SIM_CLOCK.register_timer(window_t, 150)

    dash.show()
    sensor.show()
    sys.exit(app.exec())
