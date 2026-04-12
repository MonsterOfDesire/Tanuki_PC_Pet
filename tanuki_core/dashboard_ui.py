import os

from PyQt6.QtCore import QEasingCurve, QObject, QPoint, QPropertyAnimation, QTimer, Qt, QVariantAnimation, pyqtSignal
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QLabel, QMessageBox, QProgressBar, QPushButton, QVBoxLayout, QWidget
from pynput import mouse

from .runtime import SIM_CLOCK, app_now
from .validation import build_validation_report

SAFE_WINDOW_MODE = os.environ.get("TANUKI_SAFE_WINDOW_MODE", "0") == "1"


def build_overlay_window_flags():
    flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
    if not SAFE_WINDOW_MODE:
        flags |= Qt.WindowType.Tool
    return flags


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


class Dashboard(QWidget):
    DURATION_BTN_STYLE = (
        "QPushButton { background: #f3f3f3; color: #222; border-radius: 8px; padding: 6px 10px; border: 1px solid #999; }"
        "QPushButton:checked { background: #91e08f; border: 1px solid #4a8f48; font-weight: bold; }"
    )
    SECTION_LABEL_STYLE = "color: white; background: rgba(0,0,0,150); padding: 6px 8px; border-radius: 6px;"

    def __init__(self, target_rect, pets_dict, resource_resolver):
        super().__init__()
        self.is_expanded = False
        self.config_store = None
        self.care_feature_enabled = True
        self.debug_enabled = False
        self.time_scale_options = [1, 2, 4, 8]
        self.time_scale_idx = 0
        self.time_scale_buttons = []
        self.display_scale_options = [1.0, 1.5, 2.0, 3.0]
        self.display_scale_idx = 0
        self.display_scale_buttons = []
        self.teio_dur_list = [2, 5, 10, 20, 30]
        self.teio_dur_idx = 3
        self.tsuyoshi_dur_list = [2, 10, 20, 40, 60]
        self.tsuyoshi_dur_idx = 2
        self.teio_duration_buttons = []
        self.tsuyoshi_duration_buttons = []
        self.target_rect = target_rect
        self.pets_dict = pets_dict
        self.resource_resolver = resource_resolver
        self.setWindowFlags(build_overlay_window_flags())
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.layout = QVBoxLayout()
        self.layout.setSpacing(10)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.title_label = QLabel("狸貓控制中心")
        self.title_label.setStyleSheet("color: white; background: rgba(0,0,0,150); padding: 5px; border-radius: 5px;")
        self.layout.addWidget(self.title_label)
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: white; background: rgba(70,90,120,190); padding: 6px 8px; border-radius: 6px;")
        self.status_label.hide()
        self.layout.addWidget(self.status_label)
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

        self.layout.addWidget(self.make_section_label("開發工具"))
        self.btn_debug = QPushButton("Debug: 關閉")
        self.btn_debug.clicked.connect(self.toggle_debug)
        self.layout.addWidget(self.btn_debug)

        self.btn_validate = QPushButton("檢查 Config / Manifest")
        self.btn_validate.clicked.connect(self.run_validation_checks)
        self.layout.addWidget(self.btn_validate)

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
                "QPushButton { background: white; border-radius: 8px; padding: 8px; } QPushButton:checked { background: #aaffaa; }"
            )

            mood_bar = QProgressBar()
            mood_bar.setRange(0, 100)
            mood_bar.setTextVisible(False)
            mood_bar.setFixedHeight(6)
            mood_bar.setStyleSheet(
                "QProgressBar::chunk { background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff4444, stop:1 #44ff44); } "
                "QProgressBar { background-color: #333; border-radius: 3px; }"
            )

            info["mood_bar"] = mood_bar
            info["toggle_button"] = btn

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

        ratio = self.devicePixelRatio()
        base_w, base_h = 360, 780
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
        self.update_debug_button_text()

    def refresh_mood_bars(self):
        for info in self.pets_dict.values():
            info["mood_bar"].setValue(int(info["pet"].mood_score))

    def make_section_label(self, text):
        label = QLabel(text)
        label.setStyleSheet(self.SECTION_LABEL_STYLE)
        return label

    def update_care_button_text(self):
        self.btn_care.setText(f"照護功能: {'開啟' if self.care_feature_enabled else '關閉'}")

    def update_debug_button_text(self):
        self.btn_debug.setText(f"Debug: {'開啟' if self.debug_enabled else '關閉'}")

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

    def set_debug_enabled(self, enabled, save=True):
        self.debug_enabled = bool(enabled)
        self.update_debug_button_text()
        for info in self.pets_dict.values():
            pet = info.get("pet")
            if pet:
                pet.update()

    def toggle_debug(self):
        self.set_debug_enabled(not self.debug_enabled)

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

    def run_validation_checks(self):
        assets_dir = self.resource_resolver("assets_cropped")
        config_path = self.config_store.config_path if self.config_store else self.resource_resolver("config.json")
        report, warnings = build_validation_report(assets_dir, config_path)
        if warnings:
            QMessageBox.warning(self, "檢查結果", report)
        else:
            QMessageBox.information(self, "檢查結果", report)

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
        w = self.width()
        h = self.height()
        self.show_pos = QPoint(rect.left(), rect.bottom() - h)
        self.hide_pos = QPoint(rect.left() - w - 10, rect.bottom() - h)

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


class SensorZone(QWidget):
    def __init__(self, dashboard):
        super().__init__()
        self.dashboard = dashboard
        self.setWindowFlags(build_overlay_window_flags())
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
        if self.progress >= 0.99:
            self.dashboard.slide_in([], self)
        self.progress = 0.0
        self.update()

    def enterEvent(self, event):
        if not self.dashboard.is_expanded:
            self.glow_anim.start()

    def leaveEvent(self, event):
        self.glow_anim.stop()
        self.progress = 0.0
        self.update()
