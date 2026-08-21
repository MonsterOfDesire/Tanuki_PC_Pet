from PyQt6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QSignalBlocker, QTimer, Qt, QUrl
from PyQt6.QtGui import QDesktopServices
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
from .dashboard_launcher_binding import DashboardLauncherBinding
from .dashboard_launcher_ui import (
    COLLAPSED_LAUNCHER_WIDTH,
    EXPANDED_LAUNCHER_WIDTH,
    LAUNCHER_MINIMUM_HEIGHT,
    DashboardLauncherPanel,
)
from .dashboard_presenter import DashboardPresenter
from .dashboard_shell import build_overlay_window_flags
from .dashboard_state_mapper import (
    DashboardConfigState,
    DashboardOptionBounds,
    apply_dashboard_config_to_settings,
    build_dashboard_config_state,
)
from .dashboard_tools_actions import DashboardToolsActions
from .achievement_cabinet_ui import AchievementUnlockToast
from .achievement_binding import DashboardAchievementBinding
from .achievement_presenter import build_achievement_unlock_notification
from .information_center_ui import InformationCenterWindow
from .information_center_state import InformationCenterConfigState
from .information_center_spec import (
    PAGE_ACHIEVEMENTS,
    PAGE_EVENT_LOG,
    PAGE_FAMILY_STATUS,
    PAGE_RELATION_SUMMON,
)
from .family_summary_binding import DashboardFamilySummaryBinding
from .event_log_binding import DashboardEventLogBinding
from .relation_summon_binding import DashboardRelationSummonBinding
from .offer_tray_ui import OfferTrayWindow
from .runtime import SIM_CLOCK, app_now
from .settings_provider import RuntimeSettings
from .shutdown_controller import DashboardShutdownController
from .status_settings_binding import DashboardStatusSettingsBinding
from .ui_localization import (
    character_display_name,
    localize_character_names_in_text,
    set_ui_locale,
)
from .update_runtime_controller import UpdateCheckCoordinator
from .app_version import GITHUB_RELEASES_URL


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
        self.overview_label.setText(
            localize_character_names_in_text(presentation.overview_text)
        )
        self.log_view.setPlainText(
            localize_character_names_in_text(presentation.log_text)
        )
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
        self.person_combo.currentIndexChanged.connect(
            self._handle_participant_index_changed
        )
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

    def _handle_participant_index_changed(self, index):
        participant_name = (
            self.person_combo.itemData(index, Qt.ItemDataRole.UserRole)
            if index >= 0 else
            ""
        )
        self.set_participant_name(participant_name)

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
            self.setWindowTitle(
                localize_character_names_in_text(presentation.title)
            )
            self.filter_mode = presentation.filter_mode
            self.update_filter_controls()

            current_names = [
                self.person_combo.itemData(index, Qt.ItemDataRole.UserRole)
                for index in range(self.person_combo.count())
            ]
            target_names = list(presentation.participant_names)
            if current_names != target_names:
                self.person_combo.clear()
                for character_name in target_names:
                    self.person_combo.addItem(
                        character_display_name(character_name),
                        character_name,
                    )
            if presentation.participant_name:
                index = self.person_combo.findData(
                    presentation.participant_name,
                    role=Qt.ItemDataRole.UserRole,
                )
                if index >= 0:
                    self.person_combo.setCurrentIndex(index)
            self.participant_name = presentation.participant_name
            self.log_view.setPlainText(
                localize_character_names_in_text(presentation.log_text)
            )
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
        self.table_view.setPlainText(
            localize_character_names_in_text(presentation.table_text)
        )

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
        self.social_status_enabled = bool(
            getattr(
                self.settings_provider,
                "social_status_enabled",
                False,
            )
        )
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
        self.race_frequency_options = list(
            RuntimeSettings.RACE_FREQUENCY_OPTIONS
        )
        self.race_frequency = str(
            getattr(self.settings_provider, "race_frequency", "normal")
        )
        self.chorus_frequency_options = list(
            RuntimeSettings.CHORUS_FREQUENCY_OPTIONS
        )
        self.chorus_frequency = str(
            getattr(self.settings_provider, "chorus_frequency", "normal")
        )
        self.mood_climate_options = list(
            RuntimeSettings.MOOD_CLIMATE_OPTIONS
        )
        self.mood_climate = str(
            getattr(self.settings_provider, "mood_climate", "cheerful")
        )
        self.ui_locale_options = list(RuntimeSettings.UI_LOCALE_OPTIONS)
        self.ui_locale = str(
            getattr(self.settings_provider, "ui_locale", "zh_TW")
        )
        set_ui_locale(self.ui_locale)
        self.update_check_coordinator = UpdateCheckCoordinator(parent=self)
        self.update_check_coordinator.status_changed.connect(
            lambda _status: self.refresh_information_center_settings()
        )
        self.teio_duration_buttons = []
        self.tsuyoshi_duration_buttons = []
        self.target_rect = target_rect
        self.pets_dict = pets_dict
        self.resource_resolver = resource_resolver
        self.household_state_provider = household_state_provider
        self.household_events_provider = household_events_provider
        self.activity_rhythm_provider = None
        self.household_donate_provider = household_donate_provider
        self.rudolf_work_preview_provider = None
        self.rudolf_work_preview_active_provider = None
        self.race_preview_provider = None
        self.race_preview_active_provider = None
        self.chorus_preview_provider = None
        self.chorus_preview_active_provider = None
        self.transformation_toggle_provider = None
        self.transformation_state_provider = None
        self.sleep_toggle_provider = None
        self.sleep_state_provider = None
        self.household_capture_provider = None
        self.household_load_provider = None
        self.world_mode_change_provider = None
        self.achievement_time_scale_provider = None
        self.achievement_snapshot_provider = None
        self.offer_drop_provider = None
        self.offer_hover_provider = None
        self.offer_hover_clear_provider = None
        self.sensor_zone = None
        self.household_summary_window = None
        self.social_log_window = None
        self.relationship_table_window = None
        self.offer_tray_window = None
        self.information_center_window = None
        self.achievement_unlock_toast = None
        self.launcher_shutdown_text = "關閉系統"
        self.launcher_shutdown_enabled = True
        self.launcher_status_text = ""
        self.launcher_show_status = False
        self.information_center_config_state = InformationCenterConfigState()
        self.status_settings_binding = DashboardStatusSettingsBinding(self)
        self.family_summary_binding = DashboardFamilySummaryBinding(self)
        self.achievement_binding = DashboardAchievementBinding(self)
        self.event_log_binding = DashboardEventLogBinding(self)
        self.relation_summon_binding = DashboardRelationSummonBinding(self)
        self.setWindowFlags(build_overlay_window_flags())
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.layout = QVBoxLayout()
        self.layout.setSpacing(10)
        self.layout.setContentsMargins(15, 15, 15, 15)
        title_row = QHBoxLayout()
        title_row.setSpacing(6)
        self.title_label = QLabel("狸貓控制中心")
        self.title_label.setStyleSheet("color: white; background: rgba(0,0,0,150); padding: 5px; border-radius: 5px;")
        title_row.addWidget(self.title_label, stretch=1)
        self.btn_information_center = QPushButton("資訊中心")
        self.btn_information_center.setToolTip("開啟分頁式資訊中心")
        self.btn_information_center.clicked.connect(lambda checked=False: self.open_information_center())
        title_row.addWidget(self.btn_information_center)
        self.layout.addLayout(title_row)
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

        self.layout.addWidget(
            self.make_section_label(
                f"{character_display_name('Tokai Teio')}社交冷卻"
            )
        )
        teio_row = self.create_duration_selector("teio", self.teio_dur_list)
        self.layout.addLayout(teio_row)

        self.layout.addWidget(
            self.make_section_label(
                f"{character_display_name('Tsurumaru Tsuyoshi')}社交冷卻"
            )
        )
        tsuyoshi_row = self.create_duration_selector("tsuyoshi", self.tsuyoshi_dur_list)
        self.layout.addLayout(tsuyoshi_row)

        for folder_name, info in self.pets_dict.items():
            container = QWidget()
            v_box = QVBoxLayout(container)
            v_box.setSpacing(4)
            v_box.setContentsMargins(0, 0, 0, 0)

            btn = QPushButton(
                f"召喚 {character_display_name(info['name'])}"
            )
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
        self.launcher_binding = DashboardLauncherBinding(self)
        self.launcher_panel = DashboardLauncherPanel(
            self.launcher_binding,
            resource_resolver=self.resource_resolver,
            parent=self,
        )
        self.launcher_panel.expanded_changed.connect(
            self._handle_launcher_expanded_changed
        )
        self.launcher_panel.pinned_changed.connect(
            self._handle_launcher_pinned_changed
        )
        self._activate_launcher_shell(target_rect)
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

    def _activate_launcher_shell(self, target_rect):
        self._legacy_widgets = []
        self._remove_legacy_layout_items(self.layout)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.layout.addWidget(self.launcher_panel)
        self.launcher_panel.set_pinned(False, emit_signal=False)
        self.launcher_panel.set_expanded(True, emit_signal=False)
        available_height = max(
            LAUNCHER_MINIMUM_HEIGHT,
            target_rect.height() - 20,
        )
        self.launcher_shell_height = min(520, available_height)
        self.setFixedSize(
            EXPANDED_LAUNCHER_WIDTH,
            self.launcher_shell_height,
        )
        self.launcher_panel.show()
        # Legacy mood bars no longer form part of the visible shell.
        self.update_timer.stop()

    def _remove_legacy_layout_items(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                self._legacy_widgets.append(widget)
                continue
            child_layout = item.layout()
            if child_layout is not None:
                self._remove_legacy_layout_items(child_layout)

    def set_sensor_zone(self, sensor):
        self.sensor_zone = sensor

    def _set_launcher_window_width(self, expanded):
        width = (
            EXPANDED_LAUNCHER_WIDTH
            if expanded
            else COLLAPSED_LAUNCHER_WIDTH
        )
        self.setFixedSize(width, self.launcher_shell_height)
        self.update_positions(self.target_rect)

    def _handle_launcher_expanded_changed(self, expanded):
        self._set_launcher_window_width(expanded)
        self.is_expanded = bool(expanded)
        if expanded:
            self.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents,
                False,
            )
            self.move(self.show_pos)
            self.show()
            self.raise_()
            if self.sensor_zone is not None:
                self.sensor_zone.hide()
            return
        if self.launcher_panel.is_pinned:
            self.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents,
                False,
            )
            self.move(self.show_pos)
            self.show()
            self.raise_()
            if self.sensor_zone is not None:
                self.sensor_zone.hide()
            return
        self._hide_launcher_fully()

    def _handle_launcher_pinned_changed(self, pinned):
        if pinned:
            if self.sensor_zone is not None:
                self.sensor_zone.hide()
            return
        if not self.launcher_panel.is_expanded:
            self._hide_launcher_fully()

    def _hide_launcher_fully(self):
        self.is_expanded = False
        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )
        self.update_positions(self.target_rect)
        animation = getattr(self, "anim", None)
        if animation is not None:
            animation.stop()
            animation.setEndValue(self.hide_pos)
            animation.start()
        else:
            self.move(self.hide_pos)
        if self.sensor_zone is not None:
            self.sensor_zone.show()
            self.sensor_zone.raise_()

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
            social_status_enabled=self.social_status_enabled,
            race_frequency=self.race_frequency,
            chorus_frequency=self.chorus_frequency,
            mood_climate=self.mood_climate,
            ui_locale=self.ui_locale,
            information_center=(
                self.information_center_window.capture_config_state()
                if self.information_center_window is not None
                else self.information_center_config_state
            ),
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
        self.race_frequency = str(state.race_frequency)
        self.chorus_frequency = str(state.chorus_frequency)
        self.mood_climate = str(state.mood_climate)
        self.ui_locale = str(state.ui_locale)
        set_ui_locale(self.ui_locale)
        self.information_center_config_state = state.information_center
        if self.information_center_window is not None:
            self.information_center_window.restore_config_state(
                self.information_center_config_state
            )
        self.set_debug_enabled(state.debug_enabled, save=False)
        self.set_social_status_enabled(
            state.social_status_enabled,
            save=False,
        )
        self.sync_settings_provider()
        self.update_duration_buttons()
        self.update_world_mode_buttons()
        self.update_time_scale_buttons()
        self.update_display_scale_buttons()
        self.update_household_control_states()
        self.retranslate_ui()

    def refresh_mood_bars(self):
        for info in self.pets_dict.values():
            info["mood_bar"].setValue(int(info["pet"].mood_score))

    def make_section_label(self, text):
        label = QLabel(text)
        label.setStyleSheet(self.SECTION_LABEL_STYLE)
        return label

    def update_care_button_text(self):
        self.btn_care.setText(f"照護功能: {'開啟' if self.care_feature_enabled else '關閉'}")
        self.refresh_information_center_settings()
        self.refresh_launcher_panel()

    def update_world_mode_buttons(self):
        for idx, btn in enumerate(self.world_mode_buttons):
            btn.setChecked(self.world_mode_options[idx] == self.world_mode)
        self.refresh_information_center_settings()
        self.refresh_launcher_panel()

    def update_household_control_states(self):
        golden_mode = self.world_mode == "golden_legend"
        self.btn_household_donate.setEnabled(golden_mode)
        self.btn_offer_tray.setEnabled(True)
        if (
            self.information_center_window is not None
            and self.information_center_window.is_page_visible(
                PAGE_FAMILY_STATUS
            )
        ):
            self.information_center_window.refresh_family_summary()

    def apply_debug_button_presentation(self, presentation):
        self.btn_debug.setText(presentation.text)

    def update_debug_button_text(self):
        self.apply_debug_button_presentation(self.controller.presenter.build_debug_button(self.debug_enabled))
        self.refresh_information_center_settings()

    def apply_shutdown_status_presentation(self, presentation):
        self.status_label.setText(presentation.status_text)
        self.status_label.hide()
        self.btn_exit.setEnabled(presentation.exit_enabled)
        self.btn_exit.setText(presentation.exit_text)
        self.launcher_shutdown_enabled = bool(
            presentation.exit_enabled
        )
        self.launcher_shutdown_text = str(presentation.exit_text)
        self.launcher_status_text = str(presentation.status_text)
        self.launcher_show_status = bool(presentation.show_status)
        self.refresh_launcher_panel()
        if presentation.force_expanded:
            self.launcher_panel.set_expanded(
                True,
                emit_signal=False,
            )
            self._set_launcher_window_width(True)
        self.is_expanded = bool(presentation.force_expanded)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.move(self.show_pos)
        self.show()
        self.raise_()
        if self.sensor_zone is not None:
            self.sensor_zone.hide()
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

    def set_social_status_enabled(self, enabled, save=True):
        self.controller.set_social_status_enabled(
            self,
            enabled,
            save=save,
        )

    def update_social_status_control(self):
        self.refresh_information_center_settings()

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
        self.refresh_information_center_settings()

    def update_time_scale_buttons(self):
        for idx, btn in enumerate(self.time_scale_buttons):
            btn.setChecked(idx == self.time_scale_idx)
        self.refresh_information_center_settings()
        self.refresh_launcher_panel()

    def update_display_scale_buttons(self):
        for idx, btn in enumerate(self.display_scale_buttons):
            btn.setChecked(idx == self.display_scale_idx)
        self.refresh_information_center_settings()

    def get_time_scale(self):
        return float(self.time_scale_options[self.time_scale_idx])

    def set_time_scale_index(self, index, save=True):
        self.controller.set_time_scale_index(self, index, save=save)

    def get_display_scale_multiplier(self):
        return float(self.display_scale_options[self.display_scale_idx])

    def set_display_scale_index(self, index, save=True):
        self.controller.set_display_scale_index(self, index, save=save)

    def set_race_frequency(self, value, save=True):
        self.controller.set_race_frequency(self, value, save=save)

    def set_chorus_frequency(self, value, save=True):
        self.controller.set_chorus_frequency(self, value, save=save)

    def set_mood_climate(self, value, save=True):
        self.controller.set_mood_climate(self, value, save=save)

    def set_ui_locale(self, value, save=True):
        self.controller.set_ui_locale(self, value, save=save)

    def get_update_status_snapshot(self):
        return self.update_check_coordinator.snapshot()

    def check_for_updates(self):
        return self.update_check_coordinator.start_check()

    def open_update_page(self):
        status = self.get_update_status_snapshot()
        url = (
            status.updater_download_url
            or status.release_page_url
            or GITHUB_RELEASES_URL
        )
        return QDesktopServices.openUrl(QUrl(url))

    def retranslate_ui(self):
        if self.information_center_window is not None:
            self.information_center_window.retranslate_ui()
        if self.offer_tray_window is not None:
            self.offer_tray_window.retranslate_ui()
        launcher = getattr(self, "launcher_panel", None)
        if launcher is not None and hasattr(launcher, "retranslate_ui"):
            launcher.retranslate_ui()
        self.refresh_information_center_settings()
        self.refresh_launcher_panel()

    def apply_display_scale(self, save=True):
        self.controller.apply_display_scale(self, save=save)

    def run_validation_checks(self):
        self.controller.run_validation_checks(self)

    def preview_rudolf_work(self):
        return self.controller.preview_rudolf_work(self)

    def preview_rudolf_teio_race(self):
        return self.controller.preview_rudolf_teio_race(self)

    def preview_chorus(self):
        return self.controller.preview_chorus(self)

    def toggle_transformation_preview(self, pet_name):
        return self.controller.toggle_transformation_preview(
            self,
            pet_name,
        )

    def toggle_sleep_control(self, pet_name):
        return self.controller.toggle_sleep_control(
            self,
            pet_name,
        )

    def set_household_data_providers(
        self,
        household_state_provider=None,
        household_events_provider=None,
        activity_rhythm_provider=None,
    ):
        self.household_state_provider = household_state_provider
        self.household_events_provider = household_events_provider
        self.activity_rhythm_provider = activity_rhythm_provider

    def set_achievement_data_provider(
        self,
        achievement_snapshot_provider=None,
    ):
        self.achievement_snapshot_provider = achievement_snapshot_provider

    def get_achievement_cabinet_snapshot(self):
        if callable(self.achievement_snapshot_provider):
            return self.achievement_snapshot_provider()
        return None

    def set_household_action_providers(self, household_donate_provider=None):
        self.household_donate_provider = household_donate_provider

    def set_activity_action_providers(
        self,
        rudolf_work_preview_provider=None,
        rudolf_work_preview_active_provider=None,
        race_preview_provider=None,
        race_preview_active_provider=None,
        chorus_preview_provider=None,
        chorus_preview_active_provider=None,
        transformation_toggle_provider=None,
        transformation_state_provider=None,
        sleep_toggle_provider=None,
        sleep_state_provider=None,
    ):
        self.rudolf_work_preview_provider = (
            rudolf_work_preview_provider
        )
        self.rudolf_work_preview_active_provider = (
            rudolf_work_preview_active_provider
        )
        self.race_preview_provider = race_preview_provider
        self.race_preview_active_provider = race_preview_active_provider
        self.chorus_preview_provider = chorus_preview_provider
        self.chorus_preview_active_provider = (
            chorus_preview_active_provider
        )
        self.transformation_toggle_provider = (
            transformation_toggle_provider
        )
        self.transformation_state_provider = (
            transformation_state_provider
        )
        self.sleep_toggle_provider = sleep_toggle_provider
        self.sleep_state_provider = sleep_state_provider

    def set_household_persistence_providers(
        self,
        household_capture_provider=None,
        household_load_provider=None,
        world_mode_change_provider=None,
        achievement_time_scale_provider=None,
    ):
        self.household_capture_provider = household_capture_provider
        self.household_load_provider = household_load_provider
        self.world_mode_change_provider = world_mode_change_provider
        self.achievement_time_scale_provider = (
            achievement_time_scale_provider
        )

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

    def get_activity_rhythm_snapshot(self):
        if callable(self.activity_rhythm_provider):
            return self.activity_rhythm_provider()
        return None

    def open_household_summary(self):
        self.controller.open_household_summary(self)

    def open_social_log(self):
        self.controller.open_social_log(self)

    def open_relationship_table(self):
        self.controller.open_relationship_table(self)

    def open_offer_tray(self):
        self.controller.open_offer_tray(self)

    def open_information_center(self, page_id=None):
        self.controller.open_information_center(self, page_id=page_id)

    def donate_household_fund(self, amount=100):
        self.controller.donate_household_fund(self, amount=amount)

    def apply_household_fund_donation(self, amount=100):
        if self.world_mode != "golden_legend":
            return None
        if callable(self.household_donate_provider):
            return self.household_donate_provider(amount=amount)
        return None

    def apply_rudolf_work_preview(self):
        if self.world_mode != "sandbox":
            return None
        if callable(self.rudolf_work_preview_provider):
            return self.rudolf_work_preview_provider()
        return None

    def is_rudolf_work_preview_active(self):
        if callable(self.rudolf_work_preview_active_provider):
            return bool(
                self.rudolf_work_preview_active_provider()
            )
        return False

    def apply_race_preview(self):
        if self.world_mode != "sandbox":
            return None
        if callable(self.race_preview_provider):
            return self.race_preview_provider()
        return None

    def is_race_preview_active(self):
        if callable(self.race_preview_active_provider):
            return bool(self.race_preview_active_provider())
        return False

    def apply_chorus_preview(self):
        if self.world_mode != "sandbox":
            return None
        if callable(self.chorus_preview_provider):
            return self.chorus_preview_provider()
        return None

    def is_chorus_preview_active(self):
        if callable(self.chorus_preview_active_provider):
            return bool(self.chorus_preview_active_provider())
        return False

    def apply_transformation_preview(self, pet_name):
        if self.world_mode != "sandbox":
            return None
        if callable(self.transformation_toggle_provider):
            return self.transformation_toggle_provider(
                str(pet_name or "")
            )
        return None

    def get_transformation_preview_state(self, pet_name):
        if callable(self.transformation_state_provider):
            return dict(
                self.transformation_state_provider(
                    str(pet_name or "")
                )
                or {}
            )
        return {}

    def apply_sleep_control(self, pet_name):
        if self.world_mode != "sandbox":
            return None
        if callable(self.sleep_toggle_provider):
            return self.sleep_toggle_provider(str(pet_name or ""))
        return None

    def get_sleep_control_state(self, pet_name):
        if callable(self.sleep_state_provider):
            return dict(
                self.sleep_state_provider(str(pet_name or "")) or {}
            )
        return {}

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

    def apply_achievement_time_scale_transition(self, time_scale):
        if callable(self.achievement_time_scale_provider):
            return self.achievement_time_scale_provider(float(time_scale))
        return ()

    def refresh_household_summary_if_open(self):
        if self.household_summary_window is not None and self.household_summary_window.isVisible():
            self.open_household_summary()
        if (
            self.information_center_window is not None
            and self.information_center_window.is_page_visible(
                PAGE_FAMILY_STATUS
            )
        ):
            self.information_center_window.refresh_family_summary()

    def show_achievement_cabinet(self):
        self.show_information_center(PAGE_ACHIEVEMENTS)
        if self.information_center_window is not None:
            self.information_center_window.refresh_achievement_cabinet(
                sync_world_mode=True
            )
        return True

    def handle_achievement_unlocks(self, achievement_ids):
        achievement_ids = tuple(achievement_ids or ())
        snapshot = self.get_achievement_cabinet_snapshot()
        if snapshot is None:
            return False
        if self.information_center_window is not None:
            self.information_center_window.refresh_family_summary()
            self.information_center_window.refresh_achievement_cabinet()
        notification = build_achievement_unlock_notification(
            snapshot,
            achievement_ids,
        )
        if notification is None:
            return False
        if self.achievement_unlock_toast is None:
            self.achievement_unlock_toast = AchievementUnlockToast(
                self.resource_resolver
            )
        return self.achievement_unlock_toast.show_notification(
            notification,
            anchor_rect=self.target_rect,
        )

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

    def get_pet_summon_states(self):
        states = []
        for info in self.pets_dict.values():
            pet = info.get("pet")
            if pet is None:
                continue
            name = str(getattr(pet, "name", "") or info.get("name", "") or "").strip()
            if name:
                states.append(
                    (
                        name,
                        bool(getattr(pet, "user_visible", False)),
                        float(getattr(pet, "mood_score", 0.0)),
                        str(getattr(pet, "mood_state", "") or ""),
                        str(
                            getattr(
                                getattr(pet, "transformation_state", None),
                                "current_form",
                                "base",
                            )
                            or "base"
                        ),
                    )
                )
        return tuple(states)

    def get_pet_by_display_name(self, pet_name):
        target_name = str(pet_name or "").strip()
        for info in self.pets_dict.values():
            pet = info.get("pet")
            if pet is None:
                continue
            name = str(getattr(pet, "name", "") or info.get("name", "") or "").strip()
            if name == target_name:
                return pet
        return None

    def sync_pet_toggle_control(self, pet, checked):
        for info in self.pets_dict.values():
            if info.get("pet") is not pet:
                continue
            button = info.get("toggle_button")
            if button is not None and button.isChecked() != bool(checked):
                blocker = QSignalBlocker(button)
                button.setChecked(bool(checked))
                del blocker
            return

    def refresh_social_log_if_open(self):
        if self.social_log_window is not None and self.social_log_window.isVisible():
            self.open_social_log()
        if (
            self.information_center_window is not None
            and self.information_center_window.is_page_visible(
                PAGE_EVENT_LOG
            )
        ):
            self.information_center_window.refresh_event_log()

    def refresh_relationship_table_if_open(self):
        if self.relationship_table_window is not None and self.relationship_table_window.isVisible():
            self.open_relationship_table()
        if (
            self.information_center_window is not None
            and self.information_center_window.is_page_visible(
                PAGE_RELATION_SUMMON
            )
        ):
            self.information_center_window.refresh_relation_summon()

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

    def show_information_center(self, page_id=None):
        if self.information_center_window is None:
            self.information_center_window = InformationCenterWindow(
                self.resource_resolver,
                status_settings_binding=self.status_settings_binding,
                family_summary_binding=self.family_summary_binding,
                event_log_binding=self.event_log_binding,
                relation_summon_binding=self.relation_summon_binding,
                achievement_binding=self.achievement_binding,
            )
            self.information_center_window.state_changed.connect(
                self._handle_information_center_state_changed
            )
            self.information_center_window.restore_config_state(
                self.information_center_config_state
            )
            restored_state = (
                self.information_center_window.capture_config_state()
            )
            if restored_state != self.information_center_config_state:
                self.information_center_config_state = restored_state
                self.schedule_save()
        else:
            self.information_center_window.set_status_settings_binding(self.status_settings_binding)
            self.information_center_window.set_family_summary_binding(self.family_summary_binding)
            self.information_center_window.set_event_log_binding(self.event_log_binding)
            self.information_center_window.set_relation_summon_binding(self.relation_summon_binding)
            self.information_center_window.set_achievement_binding(self.achievement_binding)
        if not self.information_center_window.user_position_locked:
            target_x = self.x() + self.width() + 16
            target_y = max(self.target_rect.top(), self.y())
            max_x = self.target_rect.right() - self.information_center_window.width() + 1
            max_y = self.target_rect.bottom() - self.information_center_window.height() + 1
            self.information_center_window.move_near_anchor(
                max(self.target_rect.left(), min(target_x, max_x)),
                max(self.target_rect.top(), min(target_y, max_y)),
            )
        self.information_center_window.open_page(
            page_id or self.information_center_config_state.page_id
        )

    def _handle_information_center_state_changed(self):
        if self.information_center_window is None:
            return
        self.information_center_config_state = (
            self.information_center_window.capture_config_state()
        )
        self.schedule_save()

    def refresh_information_center_settings(self):
        if self.information_center_window is not None:
            self.information_center_window.refresh_status_settings()

    def refresh_launcher_panel(self):
        launcher = getattr(self, "launcher_panel", None)
        if launcher is not None:
            launcher.refresh_from_binding()

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
        if sensor is not None:
            self.set_sensor_zone(sensor)
            sensor.hide()
        self.launcher_panel.set_expanded(
            True,
            emit_signal=False,
        )
        self._set_launcher_window_width(True)
        self.move(self.hide_pos)
        self.is_expanded = True
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.show()
        self.anim.setEndValue(self.show_pos)
        self.anim.start()
        self.raise_()

    def slide_out(self):
        if self.is_expanded:
            if self.launcher_panel.is_pinned:
                self.launcher_panel.set_expanded(False)
            else:
                self._hide_launcher_fully()
