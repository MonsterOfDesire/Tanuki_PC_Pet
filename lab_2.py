import os
import sys
import random
import math

# --- [修正 A] Nuitka 自動化路徑判定 ---
def get_base_path():
    if "__compiled__" in globals():
        # Nuitka 編譯後的真正執行目錄
        return os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.dirname(os.path.abspath(__file__))

# 不要在此手動設定 QT_QPA_PLATFORM_PLUGIN_PATH，交給 Nuitka 插件處理
# 如果真的要設，必須判定環境。但目前我們先移除干擾項目。

from PyQt6.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout, QPushButton, QMessageBox
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

# --- 全域輔助函數 ---
def get_total_virtual_geometry():
    rect = QRect()
    for screen in QApplication.screens():
        rect = rect.united(screen.geometry())
    return rect


# --- 滑鼠監聽器 (移出 main 以確保 Signal 運作安全) ---
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
            # 必須處理多螢幕可能的負座標，物理像素轉邏輯像素
            logic_point = QPoint(int(x / ratio), int(y / ratio))
            if not self.dashboard.geometry().contains(logic_point):
                self.request_slide_out.emit()


# --- 資產解析器 ---
class AssetManager:
    def __init__(self, character_path, scale_factor=0.4):
        self.character_path = character_path
        self.scale_factor = scale_factor
        self.assets = {}
        self.refresh_assets()

    # 修正：將它變成一個靜態方法或普通函數，且不要依賴 _MEIPASS (那是 PyInstaller 專用的)
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
                # 解析：動作-心情.gif (例如 move-happy.gif)
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

    def get_frames(self, purpose, action_type=None, mood="normal"):
        if purpose not in self.assets: return self.get_any_available_frames()
        available_types = self.assets[purpose]
        target_type = action_type if action_type in available_types else random.choice(list(available_types.keys()))
        mood_map = available_types[target_type]

        # 優先尋找對應心情，找不到則找 normal
        if mood in mood_map: return mood_map[mood]
        if "normal" in mood_map: return mood_map["normal"]
        return random.choice(list(mood_map.values()))

    def get_any_available_frames(self):
        for p in self.assets.values():
            for t in p.values():
                for f in t.values(): return f
        return []


# --- 儀表板視窗 ---
class Dashboard(QWidget):
    def __init__(self, target_rect, pets_dict):
        super().__init__()
        self.is_expanded = False
        self.target_rect = target_rect  # 傳入的是 leftmost_screen.availableGeometry()
        self.pets_dict = pets_dict

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.layout = QVBoxLayout()
        label = QLabel("狸貓控制中心")
        label.setStyleSheet("color: white; background: rgba(0,0,0,150); padding: 5px; border-radius: 5px;")
        self.layout.addWidget(label)

        for folder_name, info in self.pets_dict.items():
            btn = QPushButton(f"召喚 {info['name']}")
            btn.setCheckable(True)
            btn.setChecked(info["pet"].isVisible())
            btn.toggled.connect(lambda checked, p=info["pet"]: p.show() if checked else p.hide())
            btn.setStyleSheet(
                "QPushButton { background: white; border-radius: 8px; padding: 8px; } QPushButton:checked { background: #aaffaa; }")
            self.layout.addWidget(btn)

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

    def update_positions(self, rect):
        self.show_pos = QPoint(rect.left(), rect.bottom() - self.h)
        self.hide_pos = QPoint(rect.left() - self.w - 10, rect.bottom() - self.h)

    def slide_in(self, pets, sensor):
        self.is_expanded = True
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.anim.setEndValue(self.show_pos)
        self.anim.start()
        self.raise_()

    def slide_out(self):
        if self.is_expanded:
            self.is_expanded = False
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            self.anim.setEndValue(self.hide_pos)
            self.anim.start()


# --- 進度條感應區 ---
class SensorZone(QWidget):
    def __init__(self, dashboard):
        super().__init__()
        self.dashboard = dashboard
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.progress = 0.0

        self.glow_anim = QVariantAnimation(self)
        self.glow_anim.setDuration(2000)
        self.glow_anim.setStartValue(0.0)
        self.glow_anim.setEndValue(1.0)
        self.glow_anim.valueChanged.connect(self.update_progress)
        self.glow_anim.finished.connect(self.on_finished)

    def update_progress(self, value):
        self.progress = value
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setBrush(QColor(40, 40, 40, 80))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(self.rect())
        if self.progress > 0:
            fill_h = int(self.height() * self.progress)
            painter.setBrush(QColor(100, 255, 100, 200))
            painter.drawRect(0, self.height() - fill_h, self.width(), fill_h)

    def on_finished(self):
        if self.progress >= 0.99: self.dashboard.slide_in([], self)
        self.progress = 0.0
        self.update()

    def enterEvent(self, event):
        if not self.dashboard.is_expanded: self.glow_anim.start()

    def leaveEvent(self, event):
        self.glow_anim.stop()
        self.progress = 0.0
        self.update()


# --- 狸貓本體 (物理 + 心情速度關聯) ---
class TanukiPet(QWidget):
    def __init__(self, char_id, char_folder, scale=0.8):
        super().__init__()
        self.char_id = char_id
        self.asset_manager = AssetManager(char_folder, scale_factor=scale)
        self.current_frames = []
        self.frame_index = 0
        self.direction = 1  # 1: 右, -1: 左
        self.dragging = False
        self.original_face_left = True  # 假設素材預設向左

        # --- 心情系統 ---
        self.mood_score = 60.0
        self.mood_state = "normal"

        # 物理屬性
        self.vy = 0.0
        self.gravity = 1.2
        self.bounce = -0.3
        self.radius = (100 * scale)

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.next_frame)
        self.anim_timer.start(80)

        self.logic_timer = QTimer(self)
        self.logic_timer.timeout.connect(self.tick)
        self.logic_timer.start(30)

        # 心情邏輯：每 3 秒浮動一次
        self.mood_timer = QTimer(self)
        self.mood_timer.timeout.connect(self.update_mood)
        self.mood_timer.start(3000)

        self.state = "idle"
        self.state_timer = 0
        self.change_state("idle", "stand")
        self.show()

    def paintEvent(self, event):
        if not self.current_frames: return
        painter = QPainter(self)
        pixmap = self.current_frames[self.frame_index]

        # 修正太空漫步：
        # 如果素材朝左 (True) 且 direction 為 1 (向右)，則翻轉
        # 如果素材朝左 (True) 且 direction 為 -1 (向左)，則不翻轉
        should_flip = (self.direction == 1) if self.original_face_left else (self.direction == -1)

        if should_flip:
            painter.translate(self.width(), 0)
            painter.scale(-1, 1)
        painter.drawPixmap(0, 0, pixmap)

    def next_frame(self):
        if not self.current_frames or self.dragging: return
        self.frame_index = (self.frame_index + 1) % len(self.current_frames)
        self.setFixedSize(self.current_frames[self.frame_index].size())
        self.update()

    def update_mood(self):
        self.mood_score = max(0, min(100, self.mood_score + random.uniform(-5, 5)))
        old_state = self.mood_state
        if self.mood_score > 80:
            self.mood_state = "happy"
        elif self.mood_score < 30:
            self.mood_state = "sad"
        else:
            self.mood_state = "normal"

        if old_state != self.mood_state:
            self.change_state(self.state)

    def tick(self):
        if self.dragging: return
        self.apply_gravity()
        if self.vy == 0: self.update_ai_behavior()

    def apply_gravity(self):
        screen = QApplication.screenAt(self.geometry().center()) or QApplication.primaryScreen()
        floor_y = screen.availableGeometry().bottom()
        curr_rect = self.geometry()

        # 根據心情決定彈跳力 (建議值)
        bounce_map = {"happy": -0.7, "normal": -0.4, "sad": -0.1, "angry": -0.3}
        current_bounce = bounce_map.get(self.mood_state, -0.4)

        if curr_rect.bottom() < floor_y:
            self.vy += self.gravity
            self.move(self.x(), self.y() + int(self.vy))

            # 落地判定
            if self.geometry().bottom() >= floor_y:
                self.move(self.x(), floor_y - self.height())

                # 關鍵：如果垂直速度夠快，就反彈
                if abs(self.vy) > 3.0:
                    self.vy *= current_bounce
                else:
                    self.vy = 0
        else:
            # 確保不會穿透地板
            if curr_rect.bottom() > floor_y:
                self.move(self.x(), floor_y - self.height())

            # 靜止狀態下 vy 歸零
            if abs(self.vy) < 1.0:
                self.vy = 0

    def update_ai_behavior(self):
        # 心情與速度關聯表
        multipliers = {"happy": 2.5, "normal": 1.0, "sad": 0.4}
        speed_m = multipliers.get(self.mood_state, 1.0)

        self.state_timer -= 1
        if self.state_timer <= 0:
            self.state = random.choice(["idle", "move"])
            self.state_timer = random.randint(50, 100)
            if self.state == "move":
                self.direction = random.choice([-1, 1])
                self.change_state("move")
            else:
                self.change_state("idle", "stand")

        if self.state == "move":
            dx = int(2 * speed_m * self.direction)
            new_x = self.x() + dx
            v_rect = get_total_virtual_geometry()
            if new_x < v_rect.left() or new_x + self.width() > v_rect.right():
                self.direction *= -1
            else:
                self.move(new_x, self.y())

    def change_state(self, purpose, action_type=None):
        frames = self.asset_manager.get_frames(purpose, action_type, self.mood_state)
        if frames:
            self.current_frames = frames
            self.frame_index = 0

    def resolve_collision(self, all_pets):
        if self.dragging or self.vy != 0 or not self.isVisible(): return
        my_center = self.geometry().center()
        repel_x = 0.0
        for other in all_pets:
            if other == self or not other.isVisible(): continue
            dist_v = my_center - other.geometry().center()
            dist = math.hypot(dist_v.x(), dist_v.y())
            min_dist = self.radius + other.radius
            if dist < min_dist and dist > 0:
                repel_x += (dist_v.x() / dist) * (min_dist - dist) * 0.5
        if abs(repel_x) > 0.1:
            self.move(self.x() + int(repel_x), self.y())

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.vy = 0
            self.drag_pos = event.globalPosition().toPoint() - self.pos()
            self.change_state("drag")

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.move(event.globalPosition().toPoint() - self.drag_pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            self.change_state("idle")


# --- 主程式啟動 ---
if __name__ == "__main__":
    app = QApplication(sys.argv)



    # --- [修正 B] 統一使用定義好的路徑 ---
    assets_dir = AssetManager.get_resource_path("assets_cropped")

    if not os.path.exists(assets_dir):
        # 如果是在編譯後的環境，這會彈出視窗
        from PyQt6.QtWidgets import QMessageBox

        QMessageBox.critical(None, "路徑錯誤", f"找不到素材包！\n預期路徑: {assets_dir}")
        sys.exit()
    # --------------------------
    check_assets_integrity(["Symboli Rudolf", "Tokai Teio", "Sirius Symboli", "Tsurumaru Tsuyoshi", "Air Groove"])
    # 完整 5 位角色配置
    configs = [
        ("Symboli Rudolf", 0.45, "滷豆腐"),
        ("Tokai Teio", 0.35, "帝寶"),
        ("Sirius Symboli", 0.4, "天狼星叔叔"),
        ("Tsurumaru Tsuyoshi", 0.3, "鶴寶"),
        ("Air Groove", 0.4, "氣槽")
    ]

    pets_dict = {}
    pets_list = []

    for i, (f_name, scale, d_name) in enumerate(configs):
        path = os.path.join(assets_dir, f_name)
        if os.path.exists(path):
            p = TanukiPet(f_name, path, scale)
            # 初始位置散開，避免重疊崩潰
            p.move(500 + i * 80, 600)
            if f_name != "Symboli Rudolf": p.hide()
            pets_dict[f_name] = {"pet": p, "name": d_name}
            pets_list.append(p)

    # 物理碰撞
    physics_timer = QTimer()
    physics_timer.timeout.connect(lambda: [p.resolve_collision(pets_list) for p in pets_list])
    physics_timer.start(30)

    # --- 多螢幕精確定位 ---
    # 尋找 X 座標最小的螢幕 (真正的最左邊)
    leftmost_screen = min(QApplication.screens(), key=lambda s: s.geometry().x())
    avail_rect = leftmost_screen.availableGeometry()

    dash = Dashboard(avail_rect, pets_dict)
    sensor = SensorZone(dash)
    # 確保感應區緊貼該螢幕的最左側
    sensor.setGeometry(avail_rect.left(), avail_rect.bottom() - 300, 20, 300)

    mouse_monitor = GlobalMouseListener(dash)

    dash.show()
    sensor.show()
    sensor.raise_()

    sys.exit(app.exec())