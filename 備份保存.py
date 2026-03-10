import os
import sys
import random
import math
import time

# --- [修正 A] Nuitka 自動化路徑判定 ---
def get_base_path():
    if "__compiled__" in globals():
        return os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.dirname(os.path.abspath(__file__))

from PyQt6.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout, QPushButton, QMessageBox, QProgressBar
from PyQt6.QtCore import Qt, QPoint, QSize, QTimer, QPropertyAnimation, QRect, QObject, QEasingCurve, QVariantAnimation, \
    pyqtSignal
from PyQt6.QtGui import QMovie, QPainter, QColor, QPixmap, QImage
from pynput import mouse


def check_assets_integrity(required_folders):
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
    def __init__(self, character_path, scale_factor=0.4):
        self.character_path = character_path
        self.scale_factor = scale_factor
        self.assets = {}
        self.refresh_assets()

    def get_safe_frames(self, purpose, mood_list, forbidden=None):
        """
        比照 get_frames_by_score 邏輯：
        1. 在所有動作樣態中，優先尋找符合 mood_list 的表情。
        2. 絕對避開 forbidden 黑名單。
        """
        if forbidden is None: forbidden = []
        if purpose not in self.assets: return self.get_any_available_frames()

        available_types = self.assets[purpose]
        type_keys = list(available_types.keys())
        random.shuffle(type_keys)  # 增加隨機性，每次找的不一定一樣

        # --- 第一階段：跨樣態尋找「最想要」的標籤 ---
        for mood_tag in mood_list:
            for t_key in type_keys:
                mood_map = available_types[t_key]
                if mood_tag in mood_map:
                    return mood_map[mood_tag]

        # --- 第二階段：如果最想要的都沒，找「不在黑名單」的任何標籤 ---
        for t_key in type_keys:
            mood_map = available_types[t_key]
            safe_keys = [k for k in mood_map.keys() if k not in forbidden]
            if safe_keys:
                # 優先找 normal (如果它不在黑名單的話)
                if "normal" in safe_keys: return mood_map["normal"]
                return mood_map[random.choice(safe_keys)]

        # --- 最後保險 ---
        return self.get_any_available_frames()

    def get_frames_by_score(self, purpose, action_type=None, mood_score=60.0):
        if purpose not in self.assets:
            return self.get_any_available_frames()

        available_types = self.assets[purpose]

        # 1. 定義心情優先級鏈
        if mood_score < 20:
            priority_chain = ["scold", "hard-cry", "cry", "exhausted", "scared"]
            forbidden = ["happy", "smile", "confidence", "cool"]
        elif mood_score < 50:
            priority_chain = ["angry", "sad", "think", "awkward", "hurry", "effort", "sleep"]
            forbidden = ["happy", "smile", "confidence", "cool"]
        else:
            priority_chain = ["happy", "smile", "confidence", "cool", "glance"]
            forbidden = ["cry", "hard-cry", "sad", "angry", "scold"]

        # --- 【核心修正 1】優先在指定樣態搜尋 ---
        # 如果指定了 walk，就先看 walk 有沒有對應心情
        if action_type in available_types:
            mood_map = available_types[action_type]
            for mood_tag in priority_chain:
                if mood_tag in mood_map:
                    return mood_map[mood_tag]

        # --- 【核心修正 2】跨樣態搜尋 (Fallback to other types) ---
        # 如果當前樣態（如 sneak）沒哭臉，去別的樣態（如 walk）找
        type_keys = list(available_types.keys())
        random.shuffle(type_keys)
        for mood_tag in priority_chain:
            for t_key in type_keys:
                m_map = available_types[t_key]
                if mood_tag in m_map:
                    return m_map[mood_tag]

        # 4. 最後的安全隨機（避開禁項）
        target_map = available_types.get(action_type, random.choice(list(available_types.values())))
        safe_keys = [k for k in target_map.keys() if k not in forbidden]
        if safe_keys:
            return target_map[random.choice(safe_keys)]

        return self.get_any_available_frames()

    @staticmethod
    def get_resource_path(relative_path):
        base = get_base_path()
        return os.path.join(base, relative_path)

    def refresh_assets(self):
        if not os.path.exists(self.character_path): return
        files = [f for f in os.listdir(self.character_path) if f.endswith(".gif")]
        for file in files:
            try:
                base_name, _ = os.path.splitext(file)
                if "-" in base_name:
                    action_part, mood = base_name.split("-", 1)
                else:
                    action_part, mood = base_name, "normal"
                parts = action_part.split("_", 1)
                purpose = parts[0]
                action_type = parts[1] if len(parts) > 1 else "default"
                frames = self.extract_frames(os.path.join(self.character_path, file))
                if frames:
                    if purpose not in self.assets: self.assets[purpose] = {}
                    if action_type not in self.assets[purpose]: self.assets[purpose][action_type] = {}
                    self.assets[purpose][action_type][mood] = frames
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

class Dashboard(QWidget):
    def __init__(self, target_rect, pets_dict):
        super().__init__()
        self.is_expanded = False
        self.target_rect = target_rect
        self.pets_dict = pets_dict
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.layout = QVBoxLayout()
        label = QLabel("狸貓控制中心")
        label.setStyleSheet("color: white; background: rgba(0,0,0,150); padding: 5px; border-radius: 5px;")
        self.layout.addWidget(label)
        for folder_name, info in self.pets_dict.items():
            container = QWidget()
            v_box = QVBoxLayout(container)
            btn = QPushButton(f"召喚 {info['name']}")
            btn.setCheckable(True)
            btn.setChecked(info["pet"].isVisible())
            btn.toggled.connect(lambda checked, p=info["pet"]: p.show() if checked else p.hide())
            btn.setStyleSheet("QPushButton { background: white; border-radius: 8px; padding: 8px; } QPushButton:checked { background: #aaffaa; }")
            mood_bar = QProgressBar()
            mood_bar.setRange(0, 100)
            mood_bar.setTextVisible(False)
            mood_bar.setFixedHeight(6)
            mood_bar.setStyleSheet("QProgressBar::chunk { background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff4444, stop:1 #44ff44); } QProgressBar { background-color: #333; border-radius: 3px; }")
            v_box.addWidget(btn)
            v_box.addWidget(mood_bar)
            self.layout.addWidget(container)
            info["mood_bar"] = mood_bar
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.refresh_mood_bars)
        self.update_timer.start(500)
        self.btn_exit = QPushButton("關閉系統")
        self.btn_exit.clicked.connect(QApplication.quit)
        self.layout.addWidget(self.btn_exit)
        self.setLayout(self.layout)
        ratio = self.devicePixelRatio()
        self.w, self.h = int(200 * ratio), int(420 * ratio)
        self.setFixedSize(self.w, self.h)
        self.update_positions(target_rect)
        self.move(self.hide_pos)
        self.anim = QPropertyAnimation(self, b"pos")
        self.anim.setDuration(400)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    def refresh_mood_bars(self):
        for info in self.pets_dict.values():
            info["mood_bar"].setValue(int(info["pet"].mood_score))
    def update_positions(self, rect):
        self.show_pos = QPoint(rect.left(), rect.bottom() - self.h)
        self.hide_pos = QPoint(rect.left() - self.w - 10, rect.bottom() - self.h)
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
    def __init__(self, char_id, char_folder, scale=0.8):
        super().__init__()
        self.char_id = char_id; self.name = char_id
        self.asset_manager = AssetManager(char_folder, scale_factor=scale)
        self.current_frames = []; self.frame_index = 0; self.direction = 1
        self.dragging = False; self.original_face_left = True
        self.mood_score = 60.0; self.mood_state = "normal"; self.drag_start_time = 0
        # --- [新增] 連點與鎖定機制變數 ---
        self.click_count = 0
        self.is_angry_locked = False
        self.click_reset_timer = QTimer(self)
        self.click_reset_timer.setSingleShot(True)
        self.click_reset_timer.timeout.connect(self.reset_clicks)

        self.lock_timer = QTimer(self)
        self.lock_timer.setSingleShot(True)
        self.lock_timer.timeout.connect(self.unlock_interaction)

        # --- [新增] 行為控制 ---
        self.state = "idle"
        self.state_timer = 0
        self.current_purpose = ""
        self.is_adult = self.name in ["Symboli Rudolf", "Sirius Symboli", "Air Groove"]
        self.lonely_timer = 0
        self.setFixedSize(int(600 * scale), int(600 * scale))


        # --- 新增：血條與淡入動畫屬性 ---
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
        self.radius = (100 * scale); self.mass = 2 if self.is_adult else 0.6
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.anim_timer = QTimer(self); self.anim_timer.timeout.connect(self.next_frame); self.anim_timer.start(80)
        self.logic_timer = QTimer(self); self.logic_timer.timeout.connect(self.tick); self.logic_timer.start(30)
        self.current_speed = 0.0  # 新增：當前實際速度
        self.state = "idle";
        self.state_timer = 0;
        self.change_state("idle", "stand");
        self.last_x = self.x()
        self.stuck_count = 0  # 紀錄卡住的次數
        self.show()

    def reset_clicks(self):
        self.click_count = 0

    def unlock_interaction(self):
        self.is_angry_locked = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.change_state("idle", "stand")

    def update_bar_opacity(self, value):
        self.bar_opacity = value; self.update()

    def animate_heart(self, value):
        self.heart_opacity = 1.0 - (value ** 2); self.heart_y_offset = int(value * 60); self.update()

    def pop_heart(self):
        if not self.heart_pixmap.isNull(): self.show_heart = True; self.heart_anim.start()

    def paintEvent(self, event):
        if not self.current_frames: return
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pixmap = self.current_frames[self.frame_index]
        draw_x = (self.width() - pixmap.width()) // 2
        draw_y = self.height() - pixmap.height()

        painter.save()
        should_flip = (self.direction == 1) if self.original_face_left else (self.direction == -1)
        if should_flip:
            painter.translate(self.width(), 0); painter.scale(-1, 1)
            painter.drawPixmap(self.width() - draw_x - pixmap.width(), draw_y, pixmap)
        else:
            painter.drawPixmap(draw_x, draw_y, pixmap)
        painter.restore()

        # --- 新增：頭頂血條繪製 ---
        if self.bar_opacity > 0:
            painter.setOpacity(self.bar_opacity)
            bar_w, bar_h = 60, 5
            bar_x = (self.width() - bar_w) // 2
            bar_y = draw_y - 12 # 位於馬娘頭頂上方
            painter.setBrush(QColor(0, 0, 0, 120)); painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 2, 2)
            color = QColor(255, 50, 50) if self.mood_score < 20 else QColor(255, 200, 50) if self.mood_score < 50 else QColor(80, 255, 80)
            painter.setBrush(color)
            painter.drawRoundedRect(bar_x, bar_y, int(bar_w * (self.mood_score / 100)), bar_h, 2, 2)

        if self.show_heart and not self.heart_pixmap.isNull():
            painter.setOpacity(self.heart_opacity)
            h_s = 35
            painter.drawPixmap((self.width() - h_s) // 2, draw_y - 20 - self.heart_y_offset, h_s, h_s, self.heart_pixmap)

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
        if old_s != self.mood_state: self.change_state(self.state)

    def tick(self):
        if not self.dragging:
            self.apply_gravity(); self.check_boundary_stuck()
            if self.vy == 0: self.update_ai_behavior()

    def apply_gravity(self):
        screen = QApplication.screenAt(self.geometry().center()) or QApplication.primaryScreen()
        floor_y = screen.availableGeometry().bottom()
        if self.geometry().bottom() < floor_y:
            self.vy += self.gravity;
            self.move(self.x(), self.y() + int(self.vy))
            if self.geometry().bottom() >= floor_y:
                imp = self.vy;
                self.move(self.x(), floor_y - self.height())
                if abs(imp) > 15:
                    self.mood_score -= 15
                    # [修正] 摔落時禁用正面表情
                    self.apply_reaction(["scared", "exhausted", "cry"], is_negative=True)
                    self.vy = imp * self.bounce
                elif abs(imp) > 3:
                    self.vy *= -0.4
                else:
                    self.vy = 0
        elif self.geometry().bottom() > floor_y: self.move(self.x(), floor_y - self.height())

    # --- [修正 1] 讓速度與心情線性掛鉤 ---
    def update_ai_behavior(self):
        # 如果被鎖定（生氣中），強制維持 idle 並不執行位移
        if self.is_angry_locked:
            if self.current_purpose != "idle":
                self.current_purpose = "idle"
                self.change_state("idle")
            return

        # --- [新增] 僵持判定 ---
        if self.state == "move":
            # 如果嘗試移動但實際 X 座標變化極小 (代表被推擠或撞牆)
            if abs(self.x() - self.last_x) < 0.5:
                self.stuck_count += 1
            else:
                self.stuck_count = max(0, self.stuck_count - 1)

            # 如果連續卡住超過 15 幀 (約 0.5 秒)
            if self.stuck_count > 60:
                # 50% 機率直接轉向，50% 機率直接放棄走路變成 idle
                if random.random() > 0.5:
                    self.direction *= -1
                else:
                    self.state = "idle"
                self.state_timer = random.randint(30, 80)  # 給予一段新的思考時間
                self.stuck_count = 0

        self.last_x = self.x()  # 更新座標紀錄

        self.state_timer -= 1
        if self.state_timer <= 0:
            self.state = random.choice(["idle", "move"])
            self.state_timer = random.randint(50, 150)
            self.current_purpose = ""

        base_speed = 0.4 + (self.mood_score / 100.0) * 2.6
        visual_p = "move" if (self.state == "move" and base_speed > 0.8) else "idle"

        if self.current_purpose != visual_p:
            self.current_purpose = visual_p
            self.change_state(visual_p, "walk" if visual_p == "move" else "stand")

        if self.state == "move":
            dx = base_speed * self.direction
            nx = self.x() + int(dx)
            vr = get_total_virtual_geometry()
            if nx < vr.left() or nx + self.width() > vr.right():
                self.direction *= -1
            else:
                self.move(nx, self.y())

    def check_boundary_stuck(self):
        vr = get_total_virtual_geometry()
        if self.x() < vr.left(): self.move(vr.left() + 5, self.y()); self.direction = 1
        elif self.x() + self.width() > vr.right(): self.move(vr.right() - self.width() - 5, self.y()); self.direction = -1

    def apply_reaction(self, p_list, is_negative=False):
        # 如果是負面反應，黑名單要包含所有笑臉
        forbidden_tags = ["happy", "smile", "confidence", "cool", "glance"] if is_negative else []

        # 直接交給 AssetManager 去翻遍所有樣態找
        fs = self.asset_manager.get_safe_frames("idle", p_list, forbidden=forbidden_tags)

        if fs:
            self.current_frames = fs
            self.frame_index = 0
            self.state = "idle"
            self.state_timer = 80  # 鎖定約 2.5 秒不亂動

    def cooldown_mood(self):
        if not self.dragging and self.vy == 0: self.mood_score = min(100, self.mood_score + 5)

    def change_state(self, p, a=None):
        fs = self.asset_manager.get_frames_by_score(p, a, self.mood_score)
        if fs: self.current_frames = fs; self.frame_index = 0

    # --- 物理邏輯修正：降低震動 ---
    def resolve_collision(self, all_pets):
        if self.dragging or self.vy != 0 or not self.isVisible(): return

        my_c = self.geometry().center()
        repel_x = 0.0

        # --- [修正] 動態排斥係數 ---
        # 心情極差時 ( < 20)，排斥力變得極弱，表現出一種消極感
        repel_weight = 0.2 if self.mood_score >= 20 else 0.05

        for other in all_pets:
            if other == self or not other.isVisible(): continue
            dist_v = my_c - other.geometry().center()
            dist = math.hypot(dist_v.x(), dist_v.y())

            # 讓大人的碰撞範圍稍微強勢一點
            effective_radius = self.radius + other.radius

            if dist < effective_radius:
                overlap = effective_radius - dist

                # --- 搖晃邏輯修正 ---
                if overlap > 5.0:  # 只有重疊較深時才推開
                    total_mass = self.mass + other.mass
                    ratio = (other.mass / total_mass)
                    repel_x += (dist_v.x() / (dist if dist > 0 else 1)) * overlap * ratio

                    # 如果是小孩撞大人，給大人一個微小的「心情回饋」
                    if not self.is_adult and other.is_adult:
                        # 這裡可以模擬「搖醒」的效果，讓大人的心情微幅跳動
                        other.mood_score = min(100, other.mood_score + 0.01)

        # 4. 執行平滑位移
        if abs(repel_x) > 0.5:
            # 係數調降至 0.2 (高阻尼)，讓碰撞感變得絲滑且不抖動
            self.move(self.x() + int(repel_x * repel_weight), self.y())

    def enterEvent(self, event):
        self.fade_anim.setStartValue(self.bar_opacity); self.fade_anim.setEndValue(1.0); self.fade_anim.start()
    def leaveEvent(self, event):
        self.fade_anim.setStartValue(self.bar_opacity); self.fade_anim.setEndValue(0.0); self.fade_anim.start()

    def mousePressEvent(self, event):
        if self.is_angry_locked: return  # 鎖定期間拒絕互動
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.vy = 0
            self.drag_start_time = time.time()
            self.drag_pos = event.globalPosition().toPoint() - self.pos()
            self.change_state("drag")
    def mouseMoveEvent(self, event):
        if self.dragging: self.move(event.globalPosition().toPoint() - self.drag_pos)

    def mouseReleaseEvent(self, event):
        if self.is_angry_locked: return
        if event.button() == Qt.MouseButton.LeftButton:
            dur = time.time() - self.drag_start_time
            self.dragging = False

            if dur < 0.2:  # 單次點擊
                self.click_count += 1
                self.click_reset_timer.start(3000)
                self.state = "idle"
                self.state_timer = 100

                if self.click_count >= 5:
                    self.is_angry_locked = True
                    self.mood_score = max(0, self.mood_score - 60)
                    self.setCursor(Qt.CursorShape.ForbiddenCursor)
                    # [修正] 生氣鎖定期間絕對不准笑
                    self.apply_reaction(["scold", "angry"], is_negative=True)
                    self.lock_timer.start(5000)
                else:
                    self.mood_score = min(100, self.mood_score + 8)
                    self.pop_heart()
                    self.apply_reaction(["happy", "smile"])

            elif dur > 5.0:  # 長按懲罰
                self.mood_score = max(0, self.mood_score - 25)
                # [修正] 長按懲罰絕對不准笑
                self.apply_reaction(["scold", "hard-cry", "exhausted"], is_negative=True)

            else:
                self.change_state("idle")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    assets_dir = AssetManager.get_resource_path("assets_cropped")
    if not os.path.exists(assets_dir): sys.exit()
    check_assets_integrity(["Symboli Rudolf", "Tokai Teio", "Sirius Symboli", "Tsurumaru Tsuyoshi", "Air Groove"])
    configs = [("Symboli Rudolf", 0.45, "滷豆腐"), ("Tokai Teio", 0.35, "帝寶"), ("Sirius Symboli", 0.4, "天狼星叔叔"), ("Tsurumaru Tsuyoshi", 0.3, "鶴寶"), ("Air Groove", 0.4, "氣槽")]
    pets_dict = {}; pets_list = []
    for i, (fn, sc, dn) in enumerate(configs):
        path = os.path.join(assets_dir, fn)
        if os.path.exists(path):
            p = TanukiPet(fn, path, sc); p.move(500 + i * 80, 600)
            if fn != "Symboli Rudolf": p.hide()
            pets_dict[fn] = {"pet": p, "name": dn}; pets_list.append(p)
    mood_t = QTimer(); mood_t.timeout.connect(lambda: [p.update_mood(pets_list) for p in pets_list]); mood_t.start(3000)
    phys_t = QTimer(); phys_t.timeout.connect(lambda: [p.resolve_collision(pets_list) for p in pets_list]); phys_t.start(30)
    l_screen = min(QApplication.screens(), key=lambda s: s.geometry().x()); av_rect = l_screen.availableGeometry()
    dash = Dashboard(av_rect, pets_dict); sensor = SensorZone(dash)
    sensor.setGeometry(av_rect.left(), av_rect.bottom() - 300, 20, 300)
    monitor = GlobalMouseListener(dash); dash.show(); sensor.show(); sys.exit(app.exec())