import random
import sys
import os
from PyQt6.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout, QPushButton
from PyQt6.QtCore import Qt, QPoint, QTimer, QPropertyAnimation, QRect, QObject, QEasingCurve, QVariantAnimation, QSize
from PyQt6.QtGui import QMovie, QPainter, QColor
from pynput import mouse  # 用於監聽全域點擊

# --- 資源管理器 (靜態資源池) ---
class ResourceManager:
    _cache = {}

    @classmethod
    def get_frames(cls, character_name, action):
        key = f"{character_name}_{action}"
        if key not in cls._cache:
            # 這裡實作將 GIF 拆解為 List[QPixmap] 的邏輯
            # 這樣多隻相同的角色可以共用同一組內存數據
            cls._cache[key] = cls.load_gif_frames(character_name, action)
        return cls._cache[key]

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


# --- 狸貓本體 ---
class TanukiPet(QWidget):
    def __init__(self, char_id, char_name):
        super().__init__()
        self.char_id = char_id  # 唯一識別碼
        self.char_name = char_name  # 角色資料夾名稱
        self.direction = 1  # 1: 右, -1: 左
        self.frames = []  # 當前狀態的影格列表
        self.current_frame_idx = 0

        # 物理參數
        self.radius = 50  # 碰撞半徑
        self.velocity = QPoint(0, 0)  # 當前速度向量

        # 1. 初始化視窗設定
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.SubWindow)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 2. 狀態管理
        self.state = "IDLE"
        self.direction = 1  # 1 為右, -1 為左

        # 3. 動畫標籤
        self.label = QLabel(self)
        self.movie = None

        # 4. 行為計時器 (每 100ms 更新一次物理邏輯)
        self.logic_timer = QTimer(self)
        self.logic_timer.timeout.connect(self.update_behavior)
        self.logic_timer.start(100)

        # 5. 隨機狀態切換計時器
        self.state_timer = 0

        # 6. 拖曳相關
        self.dragging = False
        self.drag_position = QPoint()

        # 初始載入
        self.change_state("IDLE")
        self.show()

    # --- Painter 翻轉邏輯 ---
    def paintEvent(self, event):
        if not self.frames: return

        painter = QPainter(self)
        pixmap = self.frames[self.current_frame_idx]

        if self.direction == -1:
            # [核心邏輯] 水平翻轉畫布
            painter.translate(self.width(), 0)
            painter.scale(-1, 1)

        painter.drawPixmap(0, 0, pixmap)

    # --- 碰撞排斥邏輯 ---
    def resolve_collision(self, others):
        repel_force = QPoint(0, 0)
        for other in others:
            if other == self: continue

            # 計算兩者中心點距離
            dist_vec = self.geometry().center() - other.geometry().center()
            distance = (dist_vec.x() ** 2 + dist_vec.y() ** 2) ** 0.5

            min_dist = self.radius + other.radius
            if distance < min_dist and distance > 0:
                # 產生排斥力：距離越近，力越大
                push_strength = (min_dist - distance) / min_dist
                repel_force += dist_vec * push_strength

        # 將排斥力套用到位置更新
        if not repel_force.isNull():
            self.move(self.pos() + repel_force)


    def change_state(self, new_state):
        self.state = new_state

        # 根據狀態選擇 GIF (這裡你可以根據實際檔名調整)
        gif_file = "idle.gif"
        if self.state == "WALK":
            gif_file = "walk.gif"
            self.state_timer = random.randint(30, 80)  # 走 3~8 秒
        elif self.state == "IDLE":
            gif_file = "idle.gif"
            self.state_timer = random.randint(20, 50)  # 站 2~5 秒
        elif self.state == "DRAG":
            # [修改 3] 從拖曳系列隨機選一個
            drag_gifs = ["drag1.gif", "drag2.gif", "drag3.gif"]
            gif_file = random.choice(drag_gifs)

        full_path = os.path.join(self.assets_path, gif_file)

        # 更新動畫
        if os.path.exists(full_path):
            self.movie = QMovie(full_path)
            # 處理鏡像 (如果向左走就翻轉動畫，這需要額外處理，暫時先換圖)
            self.label.setMovie(self.movie)
            self.movie.jumpToFrame(0)
            self.setFixedSize(self.movie.currentImage().size())
            self.label.setFixedSize(self.size())
            self.movie.start()

    def update_behavior(self):
        if self.state == "DRAG":
            return  # 拖曳中不執行自主邏輯

        self.state_timer -= 1

        # 狀態轉換邏輯
        if self.state_timer <= 0:
            next_state = random.choice(["IDLE", "WALK"])
            if next_state == "WALK":
                self.direction = random.choice([-1, 1])
            self.change_state(next_state)

        # [修改 1 & 2] 移動物理位移
        if self.state == "WALK":
            current_pos = self.pos()
            speed = 2 * self.direction
            # 更新座標 (簡易邊界檢測)
            new_x = current_pos.x() + speed
            # 避免跑出螢幕 (簡單範例，可以擴充抓取螢幕寬度)
            if new_x < 0 or new_x > QApplication.primaryScreen().geometry().width() - self.width():
                self.direction *= -1  # 撞牆回頭
            else:
                self.move(new_x, current_pos.y())

    # --- 拖曳事件 ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.change_state("DRAG")  # 切換到拖曳動畫

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.move(event.globalPosition().toPoint() - self.drag_position)

    def mouseReleaseEvent(self, event):
        if self.dragging:
            self.dragging = False
            self.change_state("IDLE")  # 放開後回到閒置


# --- 啟動入口 ---
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 產生三隻狸貓，分別給予不同的路徑或使用相同路徑
    pets = []
    for i in range(3):
        p = TanukiPet("assets/")  # 假設你把 gif 都放在 assets 資料夾
        p.move(500 + i * 200, 800)  # 散開初始位置
        pets.append(p)

    # 定位螢幕
    screens = QApplication.screens()
    target_screen = sorted(screens, key=lambda s: (s.geometry().x(), s.geometry().y()))[0]
    screen_rect = target_screen.geometry()

    # 初始化組件
    dash = Dashboard(screen_rect)
    sensor = SensorZone(dash)

    # 安裝全域點擊過濾
    mouse_monitor = GlobalMouseListener(dash)

    dash.show()
    sensor.show()

    sys.exit(app.exec())