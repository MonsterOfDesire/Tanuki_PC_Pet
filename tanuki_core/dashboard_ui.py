from PyQt6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QTimer, Qt
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QLabel, QMessageBox, QProgressBar, QPushButton, QVBoxLayout, QWidget

from .dashboard_actions import DashboardActions
from .dashboard_controller import DashboardController
from .dashboard_presenter import DashboardPresenter
from .dashboard_shell import build_overlay_window_flags
from .dashboard_state_mapper import (
    DashboardConfigState,
    DashboardOptionBounds,
    apply_dashboard_config_to_settings,
    build_dashboard_config_state,
)
from .dashboard_tools_actions import DashboardToolsActions
from .runtime import SIM_CLOCK, app_now
from .settings_provider import RuntimeSettings
from .shutdown_controller import DashboardShutdownController


class Dashboard(QWidget):
    DURATION_BTN_STYLE = (
        "QPushButton { background: #f3f3f3; color: #222; border-radius: 8px; padding: 6px 10px; border: 1px solid #999; }"
        "QPushButton:checked { background: #91e08f; border: 1px solid #4a8f48; font-weight: bold; }"
    )
    SECTION_LABEL_STYLE = "color: white; background: rgba(0,0,0,150); padding: 6px 8px; border-radius: 6px;"

    def __init__(
        self,
        target_rect,
        pets_dict,
        resource_resolver,
        settings_provider=None,
        actions=None,
        tools_actions=None,
        presenter=None,
        save_scheduler=None,
        shutdown_controller=None,
        controller=None,
    ):
        super().__init__()
        self.settings_provider = settings_provider or RuntimeSettings()
        actions = actions or DashboardActions(sim_clock=SIM_CLOCK, now_provider=app_now)
        tools_actions = tools_actions or DashboardToolsActions()
        presenter = presenter or DashboardPresenter()
        self.is_expanded = False
        self.config_store = None
        self.save_scheduler = save_scheduler
        shutdown_controller = shutdown_controller or DashboardShutdownController(
            save_before_quit=lambda: self.save_now(force=True)
        )
        self.controller = controller or DashboardController(
            actions=actions,
            tools_actions=tools_actions,
            presenter=presenter,
            shutdown_controller=shutdown_controller,
        )
        self.care_feature_enabled = bool(self.settings_provider.care_feature_enabled)
        self.debug_enabled = bool(self.settings_provider.debug_enabled)
        self.time_scale_options = list(RuntimeSettings.TIME_SCALE_OPTIONS)
        self.time_scale_idx = int(self.settings_provider.time_scale_idx)
        self.time_scale_buttons = []
        self.display_scale_options = list(RuntimeSettings.DISPLAY_SCALE_OPTIONS)
        self.display_scale_idx = int(self.settings_provider.display_scale_idx)
        self.display_scale_buttons = []
        self.teio_dur_list = list(RuntimeSettings.TEIO_DURATIONS)
        self.teio_dur_idx = int(self.settings_provider.teio_dur_idx)
        self.tsuyoshi_dur_list = list(RuntimeSettings.TSUYOSHI_DURATIONS)
        self.tsuyoshi_dur_idx = int(self.settings_provider.tsuyoshi_dur_idx)
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

    def sync_settings_provider(self):
        apply_dashboard_config_to_settings(self.settings_provider, self.capture_config_state())

    def capture_config_state(self):
        return build_dashboard_config_state(
            care_feature_enabled=self.care_feature_enabled,
            teio_dur_idx=self.teio_dur_idx,
            tsuyoshi_dur_idx=self.tsuyoshi_dur_idx,
            time_scale_idx=self.time_scale_idx,
            display_scale_idx=self.display_scale_idx,
            debug_enabled=self.debug_enabled,
        )

    def get_option_bounds(self):
        return DashboardOptionBounds(
            teio_duration_count=len(self.teio_dur_list),
            tsuyoshi_duration_count=len(self.tsuyoshi_dur_list),
            time_scale_count=len(self.time_scale_options),
            display_scale_count=len(self.display_scale_options),
        )

    def apply_config_state(self, state):
        if not isinstance(state, DashboardConfigState):
            return
        self.set_care_enabled(state.care_feature_enabled, save=False)
        self.teio_dur_idx = int(state.teio_dur_idx)
        self.tsuyoshi_dur_idx = int(state.tsuyoshi_dur_idx)
        self.time_scale_idx = int(state.time_scale_idx)
        self.display_scale_idx = int(state.display_scale_idx)
        self.set_debug_enabled(state.debug_enabled, save=False)
        self.sync_settings_provider()
        self.update_duration_buttons()
        self.update_time_scale_buttons()
        self.update_display_scale_buttons()

    def refresh_mood_bars(self):
        for info in self.pets_dict.values():
            info["mood_bar"].setValue(int(info["pet"].mood_score))

    def make_section_label(self, text):
        label = QLabel(text)
        label.setStyleSheet(self.SECTION_LABEL_STYLE)
        return label

    def update_care_button_text(self):
        self.btn_care.setText(f"照護功能: {'開啟' if self.care_feature_enabled else '關閉'}")

    def apply_debug_button_presentation(self, presentation):
        self.btn_debug.setText(presentation.text)

    def update_debug_button_text(self):
        self.apply_debug_button_presentation(self.controller.presenter.build_debug_button(self.debug_enabled))

    def apply_shutdown_status_presentation(self, presentation):
        self.status_label.setText(presentation.status_text)
        if presentation.show_status:
            self.status_label.show()
        else:
            self.status_label.hide()
        self.btn_exit.setEnabled(presentation.exit_enabled)
        self.btn_exit.setText(presentation.exit_text)
        self.is_expanded = bool(presentation.force_expanded)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.move(self.show_pos)
        self.show()
        self.raise_()
        QApplication.processEvents()

    def show_tools_dialog(self, presentation):
        if presentation.severity == "warning":
            QMessageBox.warning(self, presentation.title, presentation.message)
        else:
            QMessageBox.information(self, presentation.title, presentation.message)

    def begin_shutdown(self):
        self.controller.begin_shutdown(self)

    def schedule_save(self):
        if self.save_scheduler:
            self.save_scheduler.schedule()

    def save_now(self, force=False):
        if self.save_scheduler:
            self.save_scheduler.save_now(force=force)
        elif self.config_store:
            self.config_store.save_now(force=force)

    def set_care_enabled(self, enabled, save=True):
        self.controller.set_care_enabled(self, enabled, save=save)

    def toggle_care(self):
        self.controller.toggle_care(self)

    def set_debug_enabled(self, enabled, save=True):
        self.controller.set_debug_enabled(self, enabled, save=save)

    def toggle_debug(self):
        self.controller.toggle_debug(self)

    def handle_pet_toggle(self, pet, checked):
        self.controller.handle_pet_toggle(self, pet, checked)

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

    def set_duration(self, char, index, save=True):
        self.controller.set_duration(self, char, index, save=save)

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

    def set_time_scale_index(self, index, save=True):
        self.controller.set_time_scale_index(self, index, save=save)

    def get_display_scale_multiplier(self):
        return float(self.display_scale_options[self.display_scale_idx])

    def set_display_scale_index(self, index, save=True):
        self.controller.set_display_scale_index(self, index, save=save)

    def apply_display_scale(self, save=True):
        self.controller.apply_display_scale(self, save=save)

    def run_validation_checks(self):
        self.controller.run_validation_checks(self)

    def get_social_cooldown_label_seconds(self, pet_name):
        if pet_name == "Tokai Teio":
            return self.teio_dur_list[self.teio_dur_idx]
        if pet_name == "Tsurumaru Tsuyoshi":
            return self.tsuyoshi_dur_list[self.tsuyoshi_dur_idx]
        return 0

    def get_social_cooldown_seconds(self, pet_name):
        duration = self.get_social_cooldown_label_seconds(pet_name)
        return float(duration) if duration else 0.0

    def apply_social_settings(self, save=True):
        self.controller.apply_social_settings(self, save=save)

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
