import random
import sys
import os
from PyQt6.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout, QPushButton
from PyQt6.QtCore import Qt, QPoint, QSize, QTimer, QPropertyAnimation, QRect, QObject, QEasingCurve, QVariantAnimation
from PyQt6.QtGui import QMovie, QPainter, QColor
from pynput import mouse


# --- [第一階段優化] 資產解析器 ---
class AssetManager:
    def __init__(self, character_path):
        self.character_path = character_path
        self.assets = {}  # {purpose: {type: {mood: file_path}}}
        self.refresh_assets()

    def refresh_assets(self):
        if not os.path.exists(self.character_path):
            print(f"❌ 找不到角色資料夾: {self.character_path}")
            return

        files = [f for f in os.listdir(self.character_path) if f.endswith(".gif")]
        if not files:
            print(f"⚠️ 資料夾內沒有 GIF 檔案: {self.character_path}")
            return

        for file in files:
            try:
                base_name, _ = os.path.splitext(file)

                # [修正點] 使用 split("-", 1) 確保第一層橫線後全歸類為心情 (支援 hard-cry)
                if "-" in base_name:
                    action_part, mood = base_name.split("-", 1)
                else:
                    action_part, mood = base_name, "normal"

                # 拆分用途與類型 (如 idle_side_hug -> purpose: idle, type: side_hug)
                parts = action_part.split("_", 1)
                purpose = parts[0]
                action_type = parts[1] if len(parts) > 1 else "default"

                if purpose not in self.assets: self.assets[purpose] = {}
                if action_type not in self.assets[purpose]: self.assets[purpose][action_type] = {}

                self.assets[purpose][action_type][mood] = os.path.join(self.character_path, file)
            except Exception as e:
                print(f"跳過解析失敗檔案 {file}: {e}")

    def get_gif(self, purpose, action_type=None, mood="normal"):
        """層級尋找邏輯：精確匹配 -> 隨機類型 -> 隨機心情 -> 保底圖"""

        # 1. 如果完全沒有這個用途 (例如要求 move 但只有 idle)
        if purpose not in self.assets:
            return self.get_any_available_gif()

        # 2. 確定類型 (action_type)
        available_types = self.assets[purpose]
        target_type = action_type if action_type in available_types else random.choice(list(available_types.keys()))

        # 3. 確定心情 (mood)
        mood_map = available_types[target_type]
        if mood in mood_map: return mood_map[mood]
        if "normal" in mood_map: return mood_map["normal"]

        # 4. 該動作下隨機選一個心情
        return random.choice(list(mood_map.values()))

    def get_any_available_gif(self):
        """最終保底：隨機抓一張資料夾內的圖"""
        for purpose_dict in self.assets.values():
            for type_dict in purpose_dict.values():
                for path in type_dict.values():
                    return path
        return None


# --- 儀表板與感應區 (代碼保持不變，略) ---
# [此處保留您原有的 GlobalMouseListener, Dashboard, SensorZone 實作...]
# --- 全域點擊監聽器 ---
class GlobalMouseListener(QObject):
    def __init__(self, dashboard):
        super().__init__()
        self.dashboard = dashboard
        self.listener = mouse.Listener(on_click=self.on_click)
        self.listener.start()

    def on_click(self, x, y, button, pressed):
        if pressed and self.dashboard.is_expanded:
            # 判斷點擊是否在儀表板區域外
            if not self.dashboard.geometry().contains(QPoint(int(x), int(y))):
                QTimer.singleShot(0, self.dashboard.slide_out)

# --- 儀表板視窗 ---
class Dashboard(QWidget):
    def __init__(self, target_rect):
        super().__init__()
        self.is_expanded = False
        self.target_rect = target_rect

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # UI 樣式設定
        self.layout = QVBoxLayout()
        self.btn_exit = QPushButton("退出狸貓系統")
        self.btn_exit.setStyleSheet("""
            QPushButton {
                background: white; 
                border-radius: 10px; 
                padding: 15px; 
                font-weight: bold;
                border: 2px solid #ccc;
            }
            QPushButton:hover { background: #f0f0f0; }
        """)
        self.btn_exit.clicked.connect(QApplication.quit)
        self.layout.addWidget(self.btn_exit)
        self.setLayout(self.layout)

        # 考慮縮放的尺寸計算
        ratio = self.devicePixelRatio()
        self.w, self.h = int(180 * ratio), int(250 * ratio)
        self.setFixedSize(self.w, self.h)

        # 位置設定 (左下角)
        self.show_pos = QPoint(self.target_rect.left(), self.target_rect.bottom() - self.h)
        self.hide_pos = QPoint(self.target_rect.left() - self.w, self.target_rect.bottom() - self.h)
        self.move(self.hide_pos)

        # 動畫設定
        self.anim = QPropertyAnimation(self, b"pos")
        self.anim.setDuration(400)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def slide_in(self):
        self.is_expanded = True
        self.anim.setEndValue(self.show_pos)
        self.anim.start()

    def slide_out(self):
        if self.is_expanded:
            self.is_expanded = False
            self.anim.setEndValue(self.hide_pos)
            self.anim.start()

# --- 進度條感應區 ---
class SensorZone(QWidget):
    def __init__(self, dashboard):
        super().__init__()
        self.dashboard = dashboard
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.progress = 0.0  # 進度 0.0 ~ 1.0

        # 設定位置 (最左側左下角)
        rect = self.dashboard.target_rect
        self.h = 300
        self.setGeometry(rect.left(), rect.bottom() - self.h, 15, self.h)

        # 能量蓄力動畫 (3秒)
        self.glow_anim = QVariantAnimation(self)
        self.glow_anim.setDuration(3000)
        self.glow_anim.setStartValue(0.0)
        self.glow_anim.setEndValue(1.0)
        self.glow_anim.setEasingCurve(QEasingCurve.Type.InQuad)
        self.glow_anim.valueChanged.connect(self.update_progress)
        self.glow_anim.finished.connect(self.on_finished)

    def update_progress(self, value):
        self.progress = value
        self.update()  # 強制觸發 paintEvent

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. 繪製底色背景 (深灰色，帶透明度)
        painter.setBrush(QColor(40, 40, 40, 60))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(self.rect())

        # 2. 繪製蓄力進度 (純白色)
        if self.progress > 0:
            fill_height = int(self.height() * self.progress)
            painter.setBrush(QColor(255, 255, 255, 230))
            # 從底部向上畫
            painter.drawRect(0, self.height() - fill_height, self.width(), fill_height)

    def on_finished(self):
        if self.progress >= 0.99:
            self.dashboard.slide_in()
        self.progress = 0.0
        self.update()

    def enterEvent(self, event):
        if not self.dashboard.is_expanded:
            self.glow_anim.start()

    def leaveEvent(self, event):
        self.glow_anim.stop()
        self.progress = 0.0
        self.update()

# --- 狸貓本體 (整合 AssetManager) ---
class TanukiPet(QWidget):
    def __init__(self, char_id, char_folder):
        super().__init__()
        self.char_id = char_id
        self.char_folder = char_folder
        self.asset_manager = AssetManager(self.char_folder)

        # 初始狀態
        self.state = "idle"
        self.sub_state = "stand"
        self.mood = "smile"
        self.direction = 1

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.label = QLabel(self)
        self.movie = None

        self.logic_timer = QTimer(self)
        self.logic_timer.timeout.connect(self.update_behavior)
        self.logic_timer.start(100)
        self.state_timer = 0

        self.dragging = False
        self.drag_position = QPoint()

        # 啟動初次動畫
        self.change_state("idle", "stand")
        self.show()

    def change_state(self, purpose, action_type=None):
        self.state = purpose
        self.sub_state = action_type

        gif_path = self.asset_manager.get_gif(purpose, action_type, self.mood)

        if gif_path:
            self.movie = QMovie(gif_path)
            self.label.setMovie(self.movie)
            self.movie.jumpToFrame(0)
            gif_size = self.movie.currentImage().size()
            self.setFixedSize(gif_size)
            self.label.setFixedSize(gif_size)
            self.movie.start()
        else:
            print(f"❌ {self.char_id} 無法載入任何動畫")

    def update_behavior(self):
        if self.dragging: return
        self.state_timer -= 1
        if self.state_timer <= 0:
            # 隨機切換行為
            self.state = random.choice(["idle", "move"])
            self.direction = random.choice([-1, 1])
            self.state_timer = random.randint(30, 70)
            # 這裡不指定具體類型，讓 AssetManager 自己 Fallback
            self.change_state(self.state)

        if self.state == "move":
            self.move(self.x() + (2 * self.direction), self.y())
            # 簡易邊界回彈
            sw = QApplication.primaryScreen().geometry().width()
            if self.x() < 0 or self.x() > sw - self.width():
                self.direction *= -1

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.change_state("drag")

    def mouseReleaseEvent(self, event):
        self.dragging = False
        self.change_state("idle")


# --- 啟動入口 ---
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 請確保腳本所在資料夾下有 assets 資料夾，且內含對應名稱的子資料夾
    char_list = ["Symboli Rudolf", "Tokai Teio", "Sirius Symboli", "Tsurumaru Tsuyoshi", "Air Groove"]
    pets = []

    # 獲取當前腳本目錄，確保路徑正確
    base_path = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(base_path, "assets")

    print(f"🔍 正在檢查資源根目錄: {assets_dir}")

    for i, name in enumerate(char_list):
        folder = os.path.join(assets_dir, name)
        if os.path.exists(folder):
            print(f"✅ 成功載入角色: {name}")
            p = TanukiPet(char_id=name, char_folder=folder)
            p.move(300 + i * 150, 700)
            pets.append(p)
        else:
            print(f"❌ 找不到資料夾，跳過角色: {name}")

    # 初始化感應區與儀表板
    screens = QApplication.screens()
    target_screen = sorted(screens, key=lambda s: (s.geometry().x(), s.geometry().y()))[0]
    screen_rect = target_screen.geometry()
    dash = Dashboard(screen_rect)
    sensor = SensorZone(dash)
    mouse_monitor = GlobalMouseListener(dash)

    dash.show()
    sensor.show()

    if not pets:
        print("\n🆘 警告：沒有任何狸貓被成功實例化！請檢查 assets 資料夾結構。")

    sys.exit(app.exec())