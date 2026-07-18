from PyQt6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QTimer, Qt
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

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
from .offer_tray_ui import OfferTrayWindow
from .runtime import SIM_CLOCK, app_now
from .settings_provider import RuntimeSettings
from .shutdown_controller import DashboardShutdownController


class HouseholdSummaryWindow(QWidget):
    def __init__(self):
        super().__init__(None, Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.setWindowTitle("家庭摘要")
        self.resize(420, 520)
        self.user_position_locked = False
        self._moving_programmatically = False
        self.layout = QVBoxLayout()
        self.layout.setSpacing(8)
        self.layout.setContentsMargins(16, 16, 16, 16)

        self.overview_label = QLabel("")
        self.overview_label.setWordWrap(True)
        self.overview_label.setStyleSheet(
            "color: #f8f8f8; background: rgba(20,20,20,210); padding: 10px; border-radius: 8px;"
        )
        self.layout.addWidget(self.overview_label)

        self.log_title = QLabel("重點事件")
        self.log_title.setStyleSheet(Dashboard.SECTION_LABEL_STYLE)
        self.layout.addWidget(self.log_title)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet(
            "QPlainTextEdit { background: rgba(12,12,12,230); color: #f0f0f0; border-radius: 8px; padding: 8px; }"
        )
        self.layout.addWidget(self.log_view, stretch=1)
        self.setLayout(self.layout)

    def apply_presentation(self, presentation):
        self.setWindowTitle(presentation.title)
        self.overview_label.setText(presentation.overview_text)
        self.log_view.setPlainText(presentation.log_text)
        scroll_bar = self.log_view.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.maximum())

    def move_near_anchor(self, x, y):
        self._moving_programmatically = True
        try:
            self.move(x, y)
        finally:
            self._moving_programmatically = False

    def moveEvent(self, event):
        if not self._moving_programmatically:
            self.user_position_locked = True
        super().moveEvent(event)


class SocialLogWindow(QWidget):
    FILTER_OPTIONS = (
        ("all", "全部"),
        ("personal", "個人"),
        ("social", "社交"),
        ("economy", "經濟"),
        ("item", "道具"),
    )

    def __init__(self, refresh_handler=None):
        super().__init__(None, Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.setWindowTitle("社交紀錄")
        self.resize(520, 560)
        self.user_position_locked = False
        self._moving_programmatically = False
        self._applying_presentation = False
        self.refresh_handler = refresh_handler
        self.filter_mode = "all"
        self.participant_name = ""

        self.layout = QVBoxLayout()
        self.layout.setSpacing(8)
        self.layout.setContentsMargins(16, 16, 16, 16)

        self.filter_label = QLabel("紀錄篩選")
        self.filter_label.setStyleSheet(Dashboard.SECTION_LABEL_STYLE)
        self.layout.addWidget(self.filter_label)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(6)
        self.filter_buttons = {}
        for mode, label in self.FILTER_OPTIONS:
            button = QPushButton(label)
            button.setCheckable(True)
            button.setMinimumWidth(58)
            button.setStyleSheet(Dashboard.DURATION_BTN_STYLE)
            button.clicked.connect(lambda checked=False, selected_mode=mode: self.set_filter_mode(selected_mode))
            self.filter_buttons[mode] = button
            filter_row.addWidget(button)
        self.layout.addLayout(filter_row)

        person_row = QHBoxLayout()
        person_row.setSpacing(6)
        self.person_label = QLabel("角色")
        self.person_label.setStyleSheet("color: #f0f0f0;")
        person_row.addWidget(self.person_label)
        self.person_combo = QComboBox()
        self.person_combo.currentTextChanged.connect(self.set_participant_name)
        person_row.addWidget(self.person_combo, stretch=1)
        self.layout.addLayout(person_row)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet(
            "QPlainTextEdit { background: rgba(12,12,12,230); color: #f0f0f0; border-radius: 8px; padding: 8px; }"
        )
        self.layout.addWidget(self.log_view, stretch=1)
        self.setLayout(self.layout)
        self.update_filter_controls()

    def set_filter_mode(self, mode):
        self.filter_mode = str(mode or "all")
        self.update_filter_controls()
        self.request_refresh()

    def set_participant_name(self, participant_name):
        self.participant_name = str(participant_name or "")
        self.request_refresh()

    def request_refresh(self):
        if self._applying_presentation:
            return
        if callable(self.refresh_handler):
            self.refresh_handler()

    def update_filter_controls(self):
        for mode, button in self.filter_buttons.items():
            button.setChecked(mode == self.filter_mode)
        personal_mode = self.filter_mode == "personal"
        self.person_label.setEnabled(personal_mode)
        self.person_combo.setEnabled(personal_mode)

    def apply_presentation(self, presentation):
        self._applying_presentation = True
        try:
            self.setWindowTitle(presentation.title)
            self.filter_mode = presentation.filter_mode
            self.update_filter_controls()

            current_names = [self.person_combo.itemText(index) for index in range(self.person_combo.count())]
            target_names = list(presentation.participant_names)
            if current_names != target_names:
                self.person_combo.clear()
                self.person_combo.addItems(target_names)
            if presentation.participant_name:
                index = self.person_combo.findText(presentation.participant_name)
                if index >= 0:
                    self.person_combo.setCurrentIndex(index)
            self.participant_name = presentation.participant_name
            self.log_view.setPlainText(presentation.log_text)
            scroll_bar = self.log_view.verticalScrollBar()
            scroll_bar.setValue(scroll_bar.maximum())
        finally:
            self._applying_presentation = False

    def move_near_anchor(self, x, y):
        self._moving_programmatically = True
        try:
            self.move(x, y)
        finally:
            self._moving_programmatically = False

    def moveEvent(self, event):
        if not self._moving_programmatically:
            self.user_position_locked = True
        super().moveEvent(event)


class RelationshipTableWindow(QWidget):
    def __init__(self):
        super().__init__(None, Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.setWindowTitle("關係表")
        self.resize(560, 560)
        self.user_position_locked = False
        self._moving_programmatically = False

        self.layout = QVBoxLayout()
        self.layout.setSpacing(8)
        self.layout.setContentsMargins(16, 16, 16, 16)

        self.description_label = QLabel("每隻角色對其他角色的好感度與關係細項")
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet(Dashboard.SECTION_LABEL_STYLE)
        self.layout.addWidget(self.description_label)

        self.table_view = QPlainTextEdit()
        self.table_view.setReadOnly(True)
        self.table_view.setStyleSheet(
            "QPlainTextEdit { background: rgba(12,12,12,230); color: #f0f0f0; "
            "border-radius: 8px; padding: 8px; font-family: Consolas, 'Microsoft JhengHei'; }"
        )
        self.layout.addWidget(self.table_view, stretch=1)
        self.setLayout(self.layout)

    def apply_presentation(self, presentation):
        self.setWindowTitle(presentation.title)
        self.table_view.setPlainText(presentation.table_text)

    def move_near_anchor(self, x, y):
        self._moving_programmatically = True
        try:
            self.move(x, y)
        finally:
            self._moving_programmatically = False

    def moveEvent(self, event):
        if not self._moving_programmatically:
            self.user_position_locked = True
        super().moveEvent(event)


class Dashboard(QWidget):
    DURATION_BTN_STYLE = (
        "QPushButton { background: #f3f3f3; color: #222; border-radius: 8px; padding: 6px 10px; border: 1px solid #999; }"
        "QPushButton:checked { background: #91e08f; border: 1px solid #4a8f48; font-weight: bold; }"
    )
    SECTION_LABEL_STYLE = "color: white; background: rgba(0,0,0,150); padding: 6px 8px; border-radius: 6px;"
    WORLD_MODE_LABELS = {
        "golden_legend": "黃金傳說",
        "sandbox": "沙盒",
    }

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
        household_state_provider=None,
        household_events_provider=None,
        household_donate_provider=None,
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
        self.world_mode_options = list(RuntimeSettings.WORLD_MODE_OPTIONS)
        self.world_mode = str(
            self.settings_provider.world_mode
            if self.settings_provider.world_mode in self.world_mode_options
            else self.world_mode_options[0]
        )
        self.world_mode_buttons = []
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
        self.household_state_provider = household_state_provider
        self.household_events_provider = household_events_provider
        self.household_donate_provider = household_donate_provider
        self.household_capture_provider = None
        self.household_load_provider = None
        self.world_mode_change_provider = None
        self.offer_drop_provider = None
        self.offer_hover_provider = None
        self.offer_hover_clear_provider = None
        self.household_summary_window = None
        self.social_log_window = None
        self.relationship_table_window = None
        self.offer_tray_window = None
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

        self.layout.addWidget(self.make_section_label("世界模式"))
        world_mode_row = self.create_option_selector(
            self.world_mode_options,
            self.world_mode_buttons,
            lambda value: self.WORLD_MODE_LABELS.get(value, str(value)),
            lambda index: self.set_world_mode(self.world_mode_options[index]),
        )
        self.layout.addLayout(world_mode_row)

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

        record_row = QHBoxLayout()
        record_row.setSpacing(6)
        self.btn_household_summary = QPushButton("家庭摘要")
        self.btn_household_summary.clicked.connect(self.open_household_summary)
        record_row.addWidget(self.btn_household_summary)
        self.btn_social_log = QPushButton("社交紀錄")
        self.btn_social_log.clicked.connect(self.open_social_log)
        record_row.addWidget(self.btn_social_log)
        self.btn_relationship_table = QPushButton("關係表")
        self.btn_relationship_table.clicked.connect(self.open_relationship_table)
        record_row.addWidget(self.btn_relationship_table)
        self.layout.addLayout(record_row)

        household_action_row = QHBoxLayout()
        household_action_row.setSpacing(6)
        self.btn_household_donate = QPushButton("捐生活費 +100")
        self.btn_household_donate.clicked.connect(lambda: self.donate_household_fund(100))
        household_action_row.addWidget(self.btn_household_donate)
        self.btn_offer_tray = QPushButton("飲食托盤")
        self.btn_offer_tray.clicked.connect(self.open_offer_tray)
        household_action_row.addWidget(self.btn_offer_tray)
        self.layout.addLayout(household_action_row)

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
        self.update_world_mode_buttons()
        self.update_time_scale_buttons()
        self.update_display_scale_buttons()
        self.update_care_button_text()
        self.update_debug_button_text()
        self.update_household_control_states()

    def sync_settings_provider(self):
        apply_dashboard_config_to_settings(self.settings_provider, self.capture_config_state())

    def capture_config_state(self):
        return build_dashboard_config_state(
            world_mode=self.world_mode,
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
        self.set_world_mode(state.world_mode, save=False)
        self.set_care_enabled(state.care_feature_enabled, save=False)
        self.teio_dur_idx = int(state.teio_dur_idx)
        self.tsuyoshi_dur_idx = int(state.tsuyoshi_dur_idx)
        self.time_scale_idx = int(state.time_scale_idx)
        self.display_scale_idx = int(state.display_scale_idx)
        self.set_debug_enabled(state.debug_enabled, save=False)
        self.sync_settings_provider()
        self.update_duration_buttons()
        self.update_world_mode_buttons()
        self.update_time_scale_buttons()
        self.update_display_scale_buttons()
        self.update_household_control_states()

    def refresh_mood_bars(self):
        for info in self.pets_dict.values():
            info["mood_bar"].setValue(int(info["pet"].mood_score))

    def make_section_label(self, text):
        label = QLabel(text)
        label.setStyleSheet(self.SECTION_LABEL_STYLE)
        return label

    def update_care_button_text(self):
        self.btn_care.setText(f"照護功能: {'開啟' if self.care_feature_enabled else '關閉'}")

    def update_world_mode_buttons(self):
        for idx, btn in enumerate(self.world_mode_buttons):
            btn.setChecked(self.world_mode_options[idx] == self.world_mode)

    def update_household_control_states(self):
        golden_mode = self.world_mode == "golden_legend"
        self.btn_household_donate.setEnabled(golden_mode)
        self.btn_offer_tray.setEnabled(True)

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

    def set_world_mode(self, world_mode, save=True):
        self.controller.set_world_mode(self, world_mode, save=save)

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

    def set_household_data_providers(self, household_state_provider=None, household_events_provider=None):
        self.household_state_provider = household_state_provider
        self.household_events_provider = household_events_provider

    def set_household_action_providers(self, household_donate_provider=None):
        self.household_donate_provider = household_donate_provider

    def set_household_persistence_providers(
        self,
        household_capture_provider=None,
        household_load_provider=None,
        world_mode_change_provider=None,
    ):
        self.household_capture_provider = household_capture_provider
        self.household_load_provider = household_load_provider
        self.world_mode_change_provider = world_mode_change_provider

    def set_offer_interaction_provider(self, offer_drop_provider=None, offer_hover_provider=None, offer_hover_clear_provider=None):
        self.offer_drop_provider = offer_drop_provider
        self.offer_hover_provider = offer_hover_provider
        self.offer_hover_clear_provider = offer_hover_clear_provider

    def get_household_state_snapshot(self):
        if callable(self.household_state_provider):
            return self.household_state_provider()
        return None

    def get_recent_household_events(self, limit=24):
        if callable(self.household_events_provider):
            return list(self.household_events_provider(limit=limit))
        return []

    def open_household_summary(self):
        self.controller.open_household_summary(self)

    def open_social_log(self):
        self.controller.open_social_log(self)

    def open_relationship_table(self):
        self.controller.open_relationship_table(self)

    def open_offer_tray(self):
        self.controller.open_offer_tray(self)

    def donate_household_fund(self, amount=100):
        self.controller.donate_household_fund(self, amount=amount)

    def apply_household_fund_donation(self, amount=100):
        if self.world_mode != "golden_legend":
            return None
        if callable(self.household_donate_provider):
            return self.household_donate_provider(amount=amount)
        return None

    def capture_household_config_state(self):
        if callable(self.household_capture_provider):
            return self.household_capture_provider()
        return {}

    def apply_household_config_state(self, payload):
        if callable(self.household_load_provider):
            return self.household_load_provider(payload)
        return False

    def apply_world_mode_runtime_transition(self, world_mode, previous_mode=None):
        if callable(self.world_mode_change_provider):
            return self.world_mode_change_provider(world_mode, previous_mode=previous_mode)
        return False

    def refresh_household_summary_if_open(self):
        if self.household_summary_window is None or not self.household_summary_window.isVisible():
            return
        self.open_household_summary()

    def get_social_log_filter_mode(self):
        if self.social_log_window is not None:
            return self.social_log_window.filter_mode
        return "all"

    def get_social_log_participant_name(self):
        if self.social_log_window is not None:
            return self.social_log_window.participant_name
        return ""

    def get_pet_display_names(self):
        names = []
        for info in self.pets_dict.values():
            pet = info.get("pet")
            name = str(getattr(pet, "name", "") or "").strip()
            if not name:
                name = str(info.get("name", "") or "").strip()
            if name:
                names.append(name)
        return tuple(names)

    def refresh_social_log_if_open(self):
        if self.social_log_window is None or not self.social_log_window.isVisible():
            return
        self.open_social_log()

    def refresh_relationship_table_if_open(self):
        if self.relationship_table_window is None or not self.relationship_table_window.isVisible():
            return
        self.open_relationship_table()

    def apply_offer_item_drop(self, item_kind, global_pos):
        if callable(self.offer_drop_provider):
            return bool(self.offer_drop_provider(item_kind=item_kind, global_pos=global_pos))
        return False

    def apply_offer_item_hover(self, item_kind, global_pos):
        if callable(self.offer_hover_provider):
            return bool(self.offer_hover_provider(item_kind=item_kind, global_pos=global_pos))
        return False

    def clear_offer_item_hover(self):
        if callable(self.offer_hover_clear_provider):
            self.offer_hover_clear_provider()

    def show_household_summary(self, presentation):
        if self.household_summary_window is None:
            self.household_summary_window = HouseholdSummaryWindow()
        self.household_summary_window.apply_presentation(presentation)
        if not self.household_summary_window.user_position_locked:
            self.household_summary_window.move_near_anchor(self.x() + self.width() + 16, max(40, self.y()))
        self.household_summary_window.show()
        self.household_summary_window.raise_()
        self.household_summary_window.activateWindow()

    def show_social_log(self, presentation):
        if self.social_log_window is None:
            self.social_log_window = SocialLogWindow(refresh_handler=self.open_social_log)
        self.social_log_window.apply_presentation(presentation)
        if not self.social_log_window.user_position_locked:
            self.social_log_window.move_near_anchor(self.x() + self.width() + 16, max(40, self.y() + 80))
        self.social_log_window.show()
        self.social_log_window.raise_()
        self.social_log_window.activateWindow()

    def show_relationship_table(self, presentation):
        if self.relationship_table_window is None:
            self.relationship_table_window = RelationshipTableWindow()
        self.relationship_table_window.apply_presentation(presentation)
        if not self.relationship_table_window.user_position_locked:
            self.relationship_table_window.move_near_anchor(self.x() + self.width() + 16, max(40, self.y() + 120))
        self.relationship_table_window.show()
        self.relationship_table_window.raise_()
        self.relationship_table_window.activateWindow()

    def show_offer_tray(self):
        if self.offer_tray_window is None:
            self.offer_tray_window = OfferTrayWindow(
                drop_handler=self.apply_offer_item_drop,
                hover_handler=self.apply_offer_item_hover,
                clear_hover_handler=self.clear_offer_item_hover,
            )
        if not self.offer_tray_window.user_position_locked:
            self.offer_tray_window.move_near_anchor(self.x() + self.width() + 16, max(40, self.y() + 160))
        self.offer_tray_window.show()
        self.offer_tray_window.raise_()
        self.offer_tray_window.activateWindow()

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
