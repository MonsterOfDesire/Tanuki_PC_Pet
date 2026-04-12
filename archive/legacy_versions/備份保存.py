import os
import sys
import random
import math
import time

# --- 環境路徑初始化 ---
def get_base_path():
    # 判定程式是純 py 執行還是被 Nuitka 編譯後的環境
    if "__compiled__" in globals():
        return os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.dirname(os.path.abspath(__file__))

from PyQt6.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout, QPushButton, QMessageBox, QProgressBar
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
        self.refresh_assets()

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

    def get_frames_by_score(self, purpose, action_type=None, mood_score=60.0):
        if purpose not in self.assets:
            return self.get_any_available_frames(), "default", ""

        available_types = self.assets[purpose]

        # 1. 定義心情優先級鏈與禁止項
        if mood_score < 20:
            priority_chain = ["scold", "hard-cry", "cry", "exhausted", "scared"]
            forbidden = ["happy", "smile", "confidence", "cool"]
        elif mood_score < 50:
            priority_chain = ["angry", "sad", "think", "awkward", "hurry", "effort", "sleep"]
            forbidden = ["happy", "smile", "confidence", "cool"]
        else:
            priority_chain = ["happy", "smile", "confidence", "cool", "glance"]
            forbidden = ["cry", "hard-cry", "sad", "angry", "scold"]

        # --- 【核心修正 1】優先在指定動作搜尋 (例如 walk 裡找 cry) ---
        if action_type in available_types:
            mood_map = available_types[action_type]
            for mood_tag in priority_chain:
                if mood_tag in mood_map:
                    return mood_map[mood_tag], action_type, mood_tag

        # --- 【核心修正 2】跨動作搜尋 (例如 sneak 沒哭臉，去別的動作找哭臉) ---
        # 這是避免出現「得意臉」的關鍵，0.2.0 的精髓
        type_keys = list(available_types.keys())
        random.shuffle(type_keys)
        for mood_tag in priority_chain:
            for t_key in type_keys:
                m_map = available_types[t_key]
                if mood_tag in m_map:
                    return m_map[mood_tag], t_key, mood_tag

        # --- 【核心修正 3】最後的安全保底 (避開禁項) ---
        # 如果連跨動作都找不到情緒標籤，就在當前（或隨機）動作裡找一個「非禁項」的圖
        target_action = action_type if action_type in available_types else random.choice(list(available_types.keys()))
        target_map = available_types[target_action]

        safe_keys = [k for k in target_map.keys() if k not in forbidden]
        if safe_keys:
            chosen_mood = random.choice(safe_keys)
            return target_map[chosen_mood], target_action, chosen_mood

        # 極致保底：真的什麼都沒了
        return self.get_any_available_frames(), "default", ""

    @staticmethod
    def get_resource_path(relative_path):
        base = get_base_path()
        return os.path.join(base, relative_path)

    # 修改 AssetManager 內的 refresh_assets
    def refresh_assets(self):
        # 遍歷資料夾，將 GIF 拆解為 (目的, 動作, 情緒) 三層字典
        # 這是優化的重點：讓之後的 AI 邏輯可以精確查找「對應」的動作
        if not os.path.exists(self.character_path): return
        files = [f for f in os.listdir(self.character_path) if f.endswith(".gif")]
        for file in files:
            try:
                base_name, _ = os.path.splitext(file)
                # 嚴格分割：如果有 '-' 則取後者為 mood，否則 mood 為空 (或是動作的一部分)
                if "-" in base_name:
                    action_part, mood = base_name.split("-", 1)
                else:
                    action_part, mood = base_name, ""  # 改為空字串，不要用 normal

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

    def get_specific_frames(self, purpose, action_type, mood):
        """嚴格匹配：只有當目的、動作、情緒完全一致時才回傳"""
        try:
            return self.assets[purpose][action_type][mood]
        except KeyError:
            return None

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
    """
    1. 物理系統：apply_gravity (重力與彈跳)
    2. 狀態管理：change_state (切換素材與計時)
    3. 社交邏輯：update_ai_behavior (這就是你提到的第一點)
    4. 渲染：paintEvent (負責處理翻轉與星星/愛心特效)
    """
    def __init__(self, char_id, char_folder, scale=0.8):
        super().__init__()
        self.char_id = char_id; self.name = char_id
        self.asset_manager = AssetManager(char_folder, scale_factor=scale)
        self.current_frames = []; self.frame_index = 0; self.direction = 1
        self.dragging = False; self.original_face_left = True
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
        self.is_adult = self.name in ["Symboli Rudolf", "Sirius Symboli", "Air Groove"]
        self.lonely_timer = 0
        self.setFixedSize(int(600 * scale), int(600 * scale))
        self.social_mode = "none"
        self.social_cooldown_end = 0
        # --- 性格差異化參數設定 ---
        self.social_distance = 600  # 預設感應距離
        self.social_cooldown_duration = 5  # 預設冷卻時間(秒)

        if self.name == "Tokai Teio":  # 帝寶：愛湊熱鬧，感應遠，冷卻短
            self.social_distance = 600
            self.social_cooldown_duration = 2
        elif self.name == "Tsurumaru Tsuyoshi":  # 鶴寶：害羞體弱，感應近，冷卻長
            self.social_distance = 350
            self.social_cooldown_duration = 2
        self.current_action_tag = "stand"
        self.current_mood_tag = "happy"

        # --- 星星相關 ---
        self.star_pixmap = QPixmap(AssetManager.get_resource_path("star.png"))
        self.star_opacity = 0.0
        self.star_y_offset = 0
        self.star_anim_counter = 0
        self.star_timer = QTimer(self)
        self.star_timer.timeout.connect(self.update_star_animation)

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
        self.radius = (100 * scale); self.mass = 2 if self.is_adult else 0.8
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.anim_timer = QTimer(self); self.anim_timer.timeout.connect(self.next_frame); self.anim_timer.start(80)
        self.change_state("idle", "stand")
        self.last_x = self.x()
        self.stuck_count = 0
        self.show()

    def reset_clicks(self): self.click_count = 0
    def unlock_interaction(self):
        self.is_angry_locked = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.change_state("idle", "stand")
    def update_bar_opacity(self, value): self.bar_opacity = value; self.update()
    def animate_heart(self, value): self.heart_opacity = 1.0 - (value ** 2); self.heart_y_offset = int(value * 60); self.update()
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
            h_s = 35
            painter.drawPixmap((self.width() - h_s) // 2, draw_y - 20 - self.heart_y_offset, h_s, h_s, self.heart_pixmap)

        # --- 星星繪製 (修正位置：正確放在馬娘身上) ---
        if self.star_opacity > 0 and not self.star_pixmap.isNull():
            painter.setOpacity(self.star_opacity)
            s_size, spacing, num_stars = 25, 30, 3
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
            # 這裡傳入 self.current_action_tag
            # 觸發 0.2.0 邏輯：先找當前動作的情緒，找不到就跨動作找
            self.change_state(self.current_purpose, self.current_action_tag)

    def tick(self, all_pets):
        if not self.dragging:
            self.apply_gravity()
            self.check_boundary_stuck()
            if self.vy == 0: self.update_ai_behavior(all_pets)

    def apply_gravity(self):
        screen = QApplication.screenAt(self.geometry().center()) or QApplication.primaryScreen()
        floor_y = screen.availableGeometry().bottom()
        if self.geometry().bottom() < floor_y:
            self.vy += self.gravity; self.move(self.x(), self.y() + int(self.vy))
            if self.geometry().bottom() >= floor_y:
                imp = self.vy; self.move(self.x(), floor_y - self.height())
                if abs(imp) > 15:
                    self.mood_score -= 15
                    self.apply_reaction(["scared", "exhausted", "cry"], is_negative=True)
                    self.vy = imp * self.bounce
                elif abs(imp) > 3: self.vy *= -0.4
                else: self.vy = 0
        elif self.geometry().bottom() > floor_y: self.move(self.x(), floor_y - self.height())

    def update_star_animation(self):
        target_opacity = 1.0 if self.social_mode in ["following", "mimicking"] else 0.0
        if self.star_opacity < target_opacity: self.star_opacity = min(1.0, self.star_opacity + 0.1)
        elif self.star_opacity > target_opacity: self.star_opacity = max(0.0, self.star_opacity - 0.1)
        self.star_anim_counter = (self.star_anim_counter + 1) % 360
        self.star_y_offset = int(math.sin(self.star_anim_counter * 0.1) * 5)
        if self.star_opacity > 0: self.update()
        else: self.star_timer.stop()

    def update_ai_behavior(self, all_pets):
        if self.is_angry_locked: return

        now = time.time()
        is_child = self.name in ["Tokai Teio", "Tsurumaru Tsuyoshi"]

        if is_child and not self.dragging:
            rudolf = next((p for p in all_pets if p.name == "Symboli Rudolf" and p.isVisible()), None)

            if rudolf and now > self.social_cooldown_end:
                dist = math.hypot(self.x() - rudolf.x(), self.y() - rudolf.y())
                is_behind = (self.x() - rudolf.x()) * rudolf.direction < 0

                # --- 1. 觸發判定 (使用性格變數) ---
                if self.social_mode == "none" and dist < self.social_distance:
                    r_p = rudolf.current_purpose
                    if r_p == "move" and is_behind:
                        self.social_mode = "following"
                        self.state_timer = random.randint(200, 400)
                        self.star_timer.start(30)
                    else:
                        # 0.2.0 精確檢查：如果魯道夫目前的動作我有對應圖，才開啟模仿
                        if self.asset_manager.get_specific_frames(r_p, rudolf.current_action_tag,
                                                                  rudolf.current_mood_tag):
                            self.social_mode = "mimicking"
                            self.state_timer = random.randint(60, 80)
                            self.star_timer.start(30)

                # --- 2. 執行行為 ---
                if self.social_mode in ["following", "mimicking"]:
                    target_p = rudolf.current_purpose
                    target_a = rudolf.current_action_tag
                    target_m = rudolf.current_mood_tag

                    # 同步素材邏輯
                    if (self.current_purpose != target_p or self.current_action_tag != target_a):
                        # 0.2.0 情緒連貫機制
                        res = self.asset_manager.get_frames_by_score(target_p, target_a, self.mood_score)
                        if res and res[0] and res[1] == target_a:
                            self.current_frames, self.current_purpose, self.current_action_tag, self.current_mood_tag = \
                            res[0], target_p, res[1], res[2]
                            self.frame_index = 0
                        else:
                            # 模仿不來，中斷社交
                            self.social_mode = "none"
                            self.social_cooldown_end = now + self.social_cooldown_duration
                            self.change_state("idle")
                            return

                    if target_p == "move":
                        self.direction = rudolf.direction
                        self.move_logic()

                    # 狀態計時與距離斷開 (性格連動)
                    self.state_timer -= 1
                    if self.state_timer <= 0 or dist > (self.social_distance + 150):
                        self.social_mode = "none"
                        self.social_cooldown_end = now + self.social_cooldown_duration
                    elif self.social_mode == "mimicking" and target_p != "idle":
                        self.social_mode = "none"
                        self.social_cooldown_end = now + self.social_cooldown_duration
                    return

        # --- 以下是一般隨機 AI 邏輯 ---
        if self.state == "move":
            if abs(self.x() - self.last_x) < 0.5:
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
            self.state_timer = random.randint(100, 250)
            self.current_purpose = ""

        base_speed = 0.4 + (self.mood_score / 100.0) * 2.6
        visual_p = "move" if (self.state == "move" and base_speed > 0.8) else "idle"

        if self.current_purpose != visual_p:
            # 確保這裡的 change_state 會更新 self.current_action_tag 與 self.current_mood_tag
            self.change_state(visual_p, "walk" if visual_p == "move" else None)

        if self.state == "move":
            self.move_logic()

    def move_logic(self):
        base_speed = 0.4 + (self.mood_score / 100.0) * 2.6
        nx = self.x() + int(base_speed * self.direction); vr = get_total_virtual_geometry()
        if nx < vr.left() or nx + self.width() > vr.right(): self.direction *= -1
        else: self.move(nx, self.y())

    def check_boundary_stuck(self):
        vr = get_total_virtual_geometry()
        if self.x() < vr.left(): self.move(vr.left() + 5, self.y()); self.direction = 1
        elif self.x() + self.width() > vr.right(): self.move(vr.right() - self.width() - 5, self.y()); self.direction = -1

    def apply_reaction(self, p_list, is_negative=False):
        forbidden = ["happy", "smile", "confidence", "cool", "glance"] if is_negative else []
        fs = self.asset_manager.get_safe_frames("idle", p_list, forbidden=forbidden)
        if fs: self.current_frames, self.frame_index, self.state, self.state_timer = fs, 0, "idle", 80

    def change_state(self, p, a=None):
        # 取得素材與背後真實的 action 和 mood 標籤
        result = self.asset_manager.get_frames_by_score(p, a, self.mood_score)

        if len(result) == 3:
            fs, real_a, real_m = result
            if fs:
                self.current_frames = fs
                self.frame_index = 0
                self.current_purpose = p
                self.current_action_tag = real_a  # 更新成真實標籤，例如 'climb'
                self.current_mood_tag = real_m  # 更新成真實標籤，例如 'happy'

    def resolve_collision(self, all_pets):
        if self.dragging or self.vy != 0 or not self.isVisible(): return
        my_c = self.geometry().center(); repel_x = 0.0; repel_weight = 0.2 if self.mood_score >= 20 else 0.05
        for other in all_pets:
            if other == self or not other.isVisible(): continue
            dist_v = my_c - other.geometry().center(); dist = math.hypot(dist_v.x(), dist_v.y())
            eff_rad = self.radius + other.radius
            if dist < eff_rad:
                overlap = eff_rad - dist
                if overlap > 5.0:
                    total_mass = self.mass + other.mass
                    repel_x += (dist_v.x() / (dist if dist > 0 else 1)) * overlap * (other.mass / total_mass)
                    if not self.is_adult and other.is_adult: other.mood_score = min(100, other.mood_score + 0.01)
        if abs(repel_x) > 0.5: self.move(self.x() + int(repel_x * repel_weight), self.y())

    def enterEvent(self, event): self.fade_anim.setStartValue(self.bar_opacity); self.fade_anim.setEndValue(1.0); self.fade_anim.start()
    def leaveEvent(self, event): self.fade_anim.setStartValue(self.bar_opacity); self.fade_anim.setEndValue(0.0); self.fade_anim.start()
    def mousePressEvent(self, event):
        if self.is_angry_locked: return
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging, self.vy, self.drag_start_time = True, 0, time.time()
            self.drag_pos = event.globalPosition().toPoint() - self.pos(); self.change_state("drag")
    def mouseMoveEvent(self, event):
        if self.dragging: self.move(event.globalPosition().toPoint() - self.drag_pos)
    def mouseReleaseEvent(self, event):
        if self.is_angry_locked: return
        if event.button() == Qt.MouseButton.LeftButton:
            dur, self.dragging = time.time() - self.drag_start_time, False
            if dur < 0.2:
                self.click_count += 1; self.click_reset_timer.start(3000); self.state, self.state_timer = "idle", 100
                if self.click_count >= 5:
                    self.is_angry_locked, self.mood_score = True, max(0, self.mood_score - 60)
                    self.setCursor(Qt.CursorShape.ForbiddenCursor); self.apply_reaction(["scold", "angry"], is_negative=True); self.lock_timer.start(5000)
                else: self.mood_score = min(100, self.mood_score + 8); self.pop_heart(); self.apply_reaction(["happy", "smile"])
            elif dur > 5.0:
                self.mood_score = max(0, self.mood_score - 25); self.apply_reaction(["scold", "hard-cry", "exhausted"], is_negative=True)
            else: self.change_state("idle")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    assets_dir = AssetManager.get_resource_path("assets_cropped")
    if not os.path.exists(assets_dir): sys.exit()
    check_assets_integrity(["Symboli Rudolf", "Tokai Teio", "Sirius Symboli", "Tsurumaru Tsuyoshi", "Air Groove"])
    configs = [("Symboli Rudolf", 0.45, "滷豆腐"), ("Tokai Teio", 0.35, "帝寶"), ("Sirius Symboli", 0.4, "天狼星叔叔"), ("Tsurumaru Tsuyoshi", 0.3, "鶴寶"), ("Air Groove", 0.4, "氣槽")]
    pets_dict, pets_list = {}, []
    for i, (fn, sc, dn) in enumerate(configs):
        path = os.path.join(assets_dir, fn)
        if os.path.exists(path):
            p = TanukiPet(fn, path, sc); p.move(500 + i * 80, 600)
            if fn != "Symboli Rudolf": p.hide()
            pets_dict[fn] = {"pet": p, "name": dn}; pets_list.append(p)
    mood_t = QTimer(); mood_t.timeout.connect(lambda: [p.update_mood(pets_list) for p in pets_list]); mood_t.start(3000)
    phys_t = QTimer(); phys_t.timeout.connect(lambda: [p.resolve_collision(pets_list) for p in pets_list]); phys_t.start(30)
    logic_t = QTimer(); logic_t.timeout.connect(lambda: [p.tick(pets_list) for p in pets_list]); logic_t.start(30)
    l_screen = min(QApplication.screens(), key=lambda s: s.geometry().x()); av_rect = l_screen.availableGeometry()
    dash = Dashboard(av_rect, pets_dict); sensor = SensorZone(dash)
    sensor.setGeometry(av_rect.left(), av_rect.bottom() - 300, 20, 300)
    monitor = GlobalMouseListener(dash); dash.show(); sensor.show(); sys.exit(app.exec())