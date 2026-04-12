import os
import sys
import random
import math
import time
import json
import re
import ctypes
from ctypes import wintypes

from tanuki_core.asset_manager import AssetManager as CoreAssetManager
from tanuki_core.config_store import ConfigStore as CoreConfigStore
from tanuki_core.dashboard_ui import Dashboard as CoreDashboard, GlobalMouseListener as CoreGlobalMouseListener, SensorZone as CoreSensorZone
from tanuki_core.geometry import DesktopGeometry as CoreDesktopGeometry, PetMovementState as CorePetMovementState, SurfaceSnapshot as CoreSurfaceSnapshot, get_total_virtual_geometry as core_get_total_virtual_geometry
from tanuki_core.pet_basics import PetBasicsMixin
from tanuki_core.pet_social_care import PetSocialCareMixin
from tanuki_core.pet_windowing import PetWindowingMixin
from tanuki_core.runtime import SIM_CLOCK, app_now
from tanuki_core.window_tracker import WindowTracker as CoreWindowTracker

SAFE_WINDOW_MODE = os.environ.get("TANUKI_SAFE_WINDOW_MODE", "0") == "1"


def build_overlay_window_flags():
    flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
    if not SAFE_WINDOW_MODE:
        flags |= Qt.WindowType.Tool
    return flags


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

WindowTracker = CoreWindowTracker
GlobalMouseListener = CoreGlobalMouseListener
SurfaceSnapshot = CoreSurfaceSnapshot
PetMovementState = CorePetMovementState
DesktopGeometry = CoreDesktopGeometry
get_total_virtual_geometry = core_get_total_virtual_geometry

AssetManager = CoreAssetManager
ConfigStore = CoreConfigStore
Dashboard = CoreDashboard
SensorZone = CoreSensorZone

class TanukiPet(PetBasicsMixin, PetSocialCareMixin, PetWindowingMixin, QWidget):
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
        self.setWindowFlags(build_overlay_window_flags())
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.anim_timer = QTimer(self); self.anim_timer.timeout.connect(self.next_frame); self.anim_timer.start(80)
        SIM_CLOCK.register_timer(self.anim_timer, 80)
        self.change_state("idle", "stand")
        self.last_x = self.x()
        self.stuck_count = 0
        self.refresh_movement_state()
        self.show()

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

        if self.is_debug_enabled():
            max_debug_width = max(120, self.width() - 16)
            lines = self.wrap_debug_lines(painter.fontMetrics(), max_debug_width)
            line_h = painter.fontMetrics().height()
            box_h = (len(lines) * line_h) + 10
            box_w = min(max_debug_width, max(painter.fontMetrics().horizontalAdvance(line) for line in lines) + 12)
            painter.setBrush(QColor(10, 10, 10, 170))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(4, 4, box_w, box_h, 6, 6)
            painter.setPen(QColor(210, 255, 210))
            for idx, line in enumerate(lines):
                painter.drawText(10, 8 + line_h + (idx * line_h), line)

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
    config_store = ConfigStore(
        config_path=AssetManager.get_resource_path("config.json"),
        clamp_pet_position=DesktopGeometry.clamp_widget_position,
    )
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
    dash = Dashboard(av_rect, pets_dict, AssetManager.get_resource_path)

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

    def ensure_visible_pets():
        for pet in pets_list:
            if not getattr(pet, "user_visible", True):
                continue
            if pet.care_lock_mode == "hidden" and pet.is_under_care(app_now()):
                continue
            clamped_x, clamped_y = DesktopGeometry.clamp_widget_position(pet, pet.x(), pet.y())
            if (clamped_x, clamped_y) != (pet.x(), pet.y()):
                pet.move(clamped_x, clamped_y)
            pet.show()
            pet.raise_()
            pet.update()

    dash.show()
    sensor.show()
    QTimer.singleShot(0, ensure_visible_pets)
    QTimer.singleShot(300, ensure_visible_pets)
    sys.exit(app.exec())
