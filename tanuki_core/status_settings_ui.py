import time

from PyQt6.QtCore import QSignalBlocker, Qt, QTimer
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .ui_theme import DEFAULT_UI_THEME
from .app_version import APP_VERSION
from .ui_localization import (
    character_display_name,
    get_ui_locale,
    set_ui_locale,
    translate_ui,
)
from .ui_controls import ToggleSwitch
from .ui_typography import ui_font_pixels, ui_text_scale
from .settings_hover_help import SettingsHoverHelp
from .status_settings_art import (
    NoticeboardAction, NoticeboardLabel, NoticeboardOption, NoticeboardRail,
    NoticeboardSection, NoticeboardTab,
)
from .transformation_control_presenter import (
    TRANSFORMATION_CONTROL_NAMES,
    build_transformation_completion_text,
    build_transformation_control_presentation,
)


COMPACT_SETTINGS_WIDTH = 660
SINGLE_COLUMN_SETTINGS_WIDTH = 690
LOCALIZED_SINGLE_COLUMN_SETTINGS_WIDTH = 1040
STATUS_TAB_ORDER = ("mode", "developer")
STATUS_TAB_LABEL_KEYS = {
    "mode": ("settings.tabs.mode", "模式設定"),
    "developer": ("settings.tabs.developer", "開發工具"),
}
WORLD_MODE_LABELS = {
    "golden_legend": "黃金傳說",
    "sandbox": "沙盒",
}
RACE_FREQUENCY_LABELS = {
    "disabled": "不啟用",
    "frequent": "經常",
    "normal": "普通",
    "occasional": "偶爾",
}
MOOD_CLIMATE_LABELS = {
    "cheerful": "明朗",
    "balanced": "均衡",
    "expressive": "多彩",
}
RACE_FREQUENCY_TOOLTIPS = {
    "disabled": "不開始新的自主競賽；已開始的競賽會正常完成。",
    "frequent": "自主競賽等待與冷卻約為普通的一半。",
    "normal": "使用沙盒或黃金傳說各自的標準競賽排程。",
    "occasional": "自主競賽等待與冷卻約為普通的兩倍。",
}
CHORUS_FREQUENCY_TOOLTIPS = {
    "disabled": "不開始新的自主合奏；已開始的合奏會正常完成。",
    "frequent": "自主合奏等待、重試與冷卻約為普通的一半。",
    "normal": "使用標準自主合奏排程。",
    "occasional": "自主合奏等待、重試與冷卻約為普通的兩倍。",
}
MOOD_CLIMATE_TOOLTIPS = {
    "cheerful": (
        "每個自然心情 tick 有 50% 會變動；幅度小且明顯偏正向，"
        "低落後較容易重新露出笑容。"
    ),
    "balanced": (
        "每個自然心情 tick 有 60% 會變動；normal 時略偏負向，"
        "小孩進入 low 後才會因附近的大人得到恢復保護。"
    ),
    "expressive": (
        "每個自然心情 tick 有 90% 會變動；負向較頻繁且幅度最大，"
        "小孩遠離大人時更容易進入 severe；大人負向幅度較低，"
        "並會在 low／severe 自我調節。"
    ),
}
RUDOLF_WORK_PREVIEW_IDLE_TEXT = (
    "只播放工作與休息動畫，不套用金錢、家庭壓力或心情結算。"
)
RUDOLF_WORK_PREVIEW_ACTIVE_TEXT = (
    "魯道夫工作預覽已開始；本次不會套用任何結算。"
)
RACE_PREVIEW_IDLE_TEXT = (
    "播放魯道夫與帝寶的完整競賽；不寫入事件，也不套用數值變動。"
)
RACE_PREVIEW_ACTIVE_TEXT = (
    "魯道夫 vs 帝寶競賽預覽已開始；本次不寫入正式事件或數值。"
)
CHORUS_PREVIEW_IDLE_TEXT = (
    "立即開始一場沙盒合奏；沿用自主反應，不寫事件或套用收益。"
)
CHORUS_PREVIEW_ACTIVE_TEXT = (
    "合奏預覽已開始；本次不寫入事件，也不套用心情或關係收益。"
)
TRANSFORMATION_PREVIEW_IDLE_TEXT = (
    "沙盒也會自主變身；按鈕可手動切換形態，且不會觸發正式事件或結算。"
)
TRANSFORMATION_PREVIEW_NAMES = TRANSFORMATION_CONTROL_NAMES
SLEEP_CONTROL_NAMES = {
    "Symboli Rudolf": "魯道夫",
    "Tokai Teio": "帝寶",
    "Sirius Symboli": "天狼星",
    "Tsurumaru Tsuyoshi": "鶴寶",
    "Air Groove": "氣槽",
}
SLEEP_CONTROL_IDLE_TEXT = "指定角色睡覺或用既有 waking 流程喚醒；僅限沙盒。"


class StatusSettingsPanel(QWidget):
    def __init__(self, binding=None, parent=None, theme=DEFAULT_UI_THEME, assets=None):
        super().__init__(parent)
        self.binding = None
        self.theme = theme
        self.assets = assets
        self._refreshing = False
        self._option_signature = None
        self._last_settings_snapshot = None
        self.world_mode_buttons = []
        self.time_scale_buttons = []
        self.display_scale_buttons = []
        self.teio_duration_buttons = []
        self.tsuyoshi_duration_buttons = []
        self.race_frequency_buttons = []
        self.chorus_frequency_buttons = []
        self.mood_climate_buttons = []
        self.memory_album_mode_buttons = []
        self.memory_album_capacity_buttons = []
        self.ui_locale_buttons = []
        self.ui_text_size_buttons = []
        self._button_groups = []
        self._compact_layout = None
        self._single_column_layout = None
        self._sleep_control_columns = None
        self._noticeboard_scale = None
        self._active_tab_key = "mode"
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysShowToolTips, True)
        self._waiting_for_rudolf_work_preview = False
        self._waiting_for_race_preview = False
        self._waiting_for_chorus_preview = False
        self._pending_transformation_request = None
        self._transformation_notice_text = ""
        self._transformation_notice_until = 0.0
        self._sleep_control_notice = None
        self.rudolf_work_preview_poll_timer = QTimer(self)
        self.rudolf_work_preview_poll_timer.setInterval(250)
        self.rudolf_work_preview_poll_timer.timeout.connect(
            self._poll_rudolf_work_preview_status
        )
        self.race_preview_poll_timer = QTimer(self)
        self.race_preview_poll_timer.setInterval(250)
        self.race_preview_poll_timer.timeout.connect(
            self._poll_race_preview_status
        )
        self.chorus_preview_poll_timer = QTimer(self)
        self.chorus_preview_poll_timer.setInterval(250)
        self.chorus_preview_poll_timer.timeout.connect(
            self._poll_chorus_preview_status
        )
        self.transformation_preview_poll_timer = QTimer(self)
        self.transformation_preview_poll_timer.setInterval(100)
        self.transformation_preview_poll_timer.timeout.connect(
            self._poll_transformation_preview_status
        )

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(theme.spacing_sm)

        self.unavailable_label = QLabel("狀態設定尚未連接執行中的 Dashboard。")
        self.unavailable_label.setProperty("tanukiRole", "settingsNotice")
        self.unavailable_label.setWordWrap(True)
        root_layout.addWidget(self.unavailable_label)

        self.settings_grid = QWidget(self)
        self.grid_layout = QGridLayout(self.settings_grid)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setHorizontalSpacing(theme.spacing_md)
        self.grid_layout.setVerticalSpacing(theme.spacing_sm)

        self.runtime_group = self._create_group("執行模式")
        self.runtime_layout = QGridLayout(self.runtime_group)
        self.runtime_layout.setHorizontalSpacing(theme.spacing_sm)
        self.runtime_layout.setVerticalSpacing(theme.spacing_sm)
        self.world_mode_label = self._create_label("世界模式")
        self.runtime_layout.addWidget(self.world_mode_label, 0, 0)
        self.world_mode_control, self.world_mode_row = (
            self._create_selector_row()
        )
        self.runtime_layout.addWidget(self.world_mode_control, 0, 1)
        self.care_switch = ToggleSwitch()
        self.care_switch.setAccessibleName("啟用角色照護功能")
        self.care_switch.setToolTip(
            "允許低心情照護與相關家庭互動。"
        )
        self.care_switch.toggled.connect(self._handle_care_toggled)
        self.care_toggle_row = self._create_toggle_row(
                "啟用角色照護功能",
                self.care_switch,
        )
        self.runtime_layout.addWidget(self.care_toggle_row, 1, 0, 1, 2)

        self.timing_group = self._create_group("時間與畫面")
        self.timing_layout = QGridLayout(self.timing_group)
        self.timing_layout.setHorizontalSpacing(theme.spacing_sm)
        self.timing_layout.setVerticalSpacing(theme.spacing_sm)
        self.time_scale_label = self._create_label("時間流速")
        self.timing_layout.addWidget(self.time_scale_label, 0, 0)
        self.time_scale_control, self.time_scale_row = (
            self._create_selector_row()
        )
        self.timing_layout.addWidget(self.time_scale_control, 0, 1)
        self.display_scale_label = self._create_label("顯示比例")
        self.timing_layout.addWidget(self.display_scale_label, 1, 0)
        self.display_scale_control, self.display_scale_row = (
            self._create_selector_row()
        )
        self.timing_layout.addWidget(self.display_scale_control, 1, 1)
        self.ui_text_size_label = self._create_label("文字尺寸")
        self.ui_text_size_control, self.ui_text_size_row = self._create_selector_row()
        self.timing_layout.addWidget(self.ui_text_size_label, 2, 0)
        self.timing_layout.addWidget(self.ui_text_size_control, 2, 1)

        self.locale_update_group = self._create_group("語言與更新")
        self.locale_update_layout = QGridLayout(
            self.locale_update_group
        )
        self.locale_update_layout.setHorizontalSpacing(
            theme.spacing_sm
        )
        self.locale_update_layout.setVerticalSpacing(theme.spacing_sm)
        self.locale_label = self._create_label("介面語言")
        self.locale_update_layout.addWidget(self.locale_label, 0, 0)
        self.ui_locale_control, self.ui_locale_row = (
            self._create_selector_row()
        )
        self.locale_update_layout.addWidget(self.ui_locale_control, 0, 1)
        self.update_action_row = QHBoxLayout()
        self.update_check_button = NoticeboardAction("立即檢查更新")
        self.update_check_button.symbol = "refresh"
        self.update_check_button.primary = True
        self.update_check_button.setProperty(
            "tanukiRole",
            "settingsAction",
        )
        self.update_check_button.clicked.connect(
            self._handle_update_check
        )
        self.update_action_row.addWidget(self.update_check_button)
        self.update_open_button = NoticeboardAction("查看新版")
        self.update_open_button.setProperty(
            "tanukiRole",
            "settingsAction",
        )
        self.update_open_button.clicked.connect(
            self._handle_open_update_page
        )
        self.update_open_button.hide()
        self.update_action_row.addWidget(self.update_open_button)
        self.locale_update_layout.addLayout(
            self.update_action_row,
            1,
            0,
            1,
            2,
        )
        self.update_status_label = QLabel(f"目前版本 {APP_VERSION}")
        self.update_status_label.setProperty(
            "tanukiRole",
            "settingsNotice",
        )
        self.update_status_label.setWordWrap(True)
        self.locale_update_layout.addWidget(
            self.update_status_label,
            2,
            0,
            1,
            2,
        )

        self.social_group = self._create_group("模仿魯道夫冷卻")
        self.social_layout = QGridLayout(self.social_group)
        self.social_layout.setHorizontalSpacing(theme.spacing_sm)
        self.social_layout.setVerticalSpacing(theme.spacing_sm)
        self.teio_social_label = self._create_label(character_display_name("Tokai Teio"))
        self.social_layout.addWidget(self.teio_social_label, 0, 0)
        self.teio_duration_control, self.teio_duration_row = (
            self._create_selector_row()
        )
        self.social_layout.addWidget(self.teio_duration_control, 0, 1)
        self.tsuyoshi_social_label = self._create_label(
            character_display_name("Tsurumaru Tsuyoshi")
        )
        self.social_layout.addWidget(self.tsuyoshi_social_label, 1, 0)
        self.tsuyoshi_duration_control, self.tsuyoshi_duration_row = (
            self._create_selector_row()
        )
        self.social_layout.addWidget(self.tsuyoshi_duration_control, 1, 1)

        self.rhythm_group = self._create_group("生活節奏")
        self.rhythm_layout = QGridLayout(self.rhythm_group)
        self.rhythm_layout.setHorizontalSpacing(theme.spacing_sm)
        self.rhythm_layout.setVerticalSpacing(theme.spacing_sm)
        self.autonomous_sleep_switch = ToggleSwitch()
        self.autonomous_sleep_switch.setAccessibleName("啟用自主睡眠")
        self.autonomous_sleep_switch.setToolTip(
            "關閉後不再開始新的自主睡眠；既有睡眠會正常結束。"
        )
        self.autonomous_sleep_switch.toggled.connect(
            self._handle_autonomous_sleep_toggled
        )
        self.autonomous_sleep_toggle_row = self._create_toggle_row(
            "啟用自主睡眠",
            self.autonomous_sleep_switch,
        )
        self.rhythm_layout.addWidget(
            self.autonomous_sleep_toggle_row,
            0,
            0,
            1,
            2,
        )
        self.autonomous_transformation_switch = ToggleSwitch()
        self.autonomous_transformation_switch.setAccessibleName(
            "啟用自主變身"
        )
        self.autonomous_transformation_switch.setToolTip(
            "關閉後不再開始新的自主變身；既有變身與解除流程會正常完成。"
        )
        self.autonomous_transformation_switch.toggled.connect(
            self._handle_autonomous_transformation_toggled
        )
        self.autonomous_transformation_toggle_row = self._create_toggle_row(
            "啟用自主變身",
            self.autonomous_transformation_switch,
        )
        self.rhythm_layout.addWidget(
            self.autonomous_transformation_toggle_row,
            1,
            0,
            1,
            2,
        )
        self.race_frequency_label = self._create_label("競賽頻率")
        self.race_frequency_label.setToolTip(
            "調整自主競賽的等待與冷卻時間；不略過資格、距離或接受判定。"
        )
        self.rhythm_layout.addWidget(self.race_frequency_label, 2, 0)
        self.race_frequency_control, self.race_frequency_row = (
            self._create_selector_row()
        )
        self.rhythm_layout.addWidget(self.race_frequency_control, 2, 1)
        self.chorus_frequency_label = self._create_label("合奏頻率")
        self.chorus_frequency_label.setToolTip(
            "調整自主合奏的等待、重試與冷卻時間；不略過資格、距離或反應判定。"
        )
        self.rhythm_layout.addWidget(self.chorus_frequency_label, 3, 0)
        self.chorus_frequency_control, self.chorus_frequency_row = (
            self._create_selector_row()
        )
        self.rhythm_layout.addWidget(self.chorus_frequency_control, 3, 1)
        self.mood_climate_label = self._create_label("情緒氣候")
        self.mood_climate_label.setToolTip(
            "自然心情會隨模擬倍速更新；三種氣候只調整發生率、正負傾向與幅度，"
            "不設定目標心情。"
        )
        self.rhythm_layout.addWidget(self.mood_climate_label, 4, 0)
        self.mood_climate_control, self.mood_climate_row = (
            self._create_selector_row()
        )
        self.rhythm_layout.addWidget(self.mood_climate_control, 4, 1)

        self.memory_group = self._create_group("回憶相簿")
        self.memory_layout = QGridLayout(self.memory_group)
        self.memory_layout.setHorizontalSpacing(theme.spacing_sm)
        self.memory_layout.setVerticalSpacing(theme.spacing_sm)
        self.memory_mode_label = self._create_label("拍照模式")
        self.memory_layout.addWidget(self.memory_mode_label, 0, 0)
        self.memory_album_mode_control, self.memory_album_mode_row = (
            self._create_selector_row()
        )
        self.memory_layout.addWidget(self.memory_album_mode_control, 0, 1)
        self.memory_capacity_label = self._create_label("照片上限")
        self.memory_layout.addWidget(self.memory_capacity_label, 1, 0)
        (
            self.memory_album_capacity_control,
            self.memory_album_capacity_row,
        ) = self._create_selector_row()
        self.memory_layout.addWidget(
            self.memory_album_capacity_control,
            1,
            1,
        )
        self.memory_settings_note = QLabel(
            "只在 1x 自動拍攝；達到上限後停止拍攝，既有照片不會自動刪除。"
        )
        self.memory_settings_note.setProperty(
            "tanukiRole",
            "settingsNotice",
        )
        self.memory_settings_note.setWordWrap(True)
        self.memory_layout.addWidget(
            self.memory_settings_note,
            2,
            0,
            1,
            2,
        )

        self.developer_group = self._create_group("開發工具")
        self.developer_layout = QVBoxLayout(self.developer_group)
        self.developer_layout.setSpacing(theme.spacing_sm)
        self.debug_switch = ToggleSwitch()
        self.debug_switch.setAccessibleName("顯示角色 Debug 資訊")
        self.debug_switch.setToolTip("顯示完整角色與效能偵錯資訊。")
        self.debug_switch.toggled.connect(self._handle_debug_toggled)
        self.debug_toggle_row = self._create_toggle_row(
                "顯示角色 Debug 資訊",
                self.debug_switch,
        )
        self.developer_layout.addWidget(self.debug_toggle_row)
        self.social_status_switch = ToggleSwitch()
        self.social_status_switch.setAccessibleName(
            "顯示角色社交狀態標籤"
        )
        self.social_status_switch.setToolTip(
            "在角色頭上顯示 random、relation_watch 等行為測試標籤。"
        )
        self.social_status_switch.toggled.connect(
            self._handle_social_status_toggled
        )
        self.social_status_toggle_row = self._create_toggle_row(
                "顯示角色社交狀態標籤",
                self.social_status_switch,
        )
        self.developer_layout.addWidget(self.social_status_toggle_row)
        self.rudolf_work_preview_button = NoticeboardAction(
            "預覽魯道夫工作"
        )
        self.rudolf_work_preview_button.setProperty(
            "tanukiRole",
            "settingsAction",
        )
        self.rudolf_work_preview_button.setAccessibleName(
            "預覽魯道夫工作"
        )
        self.rudolf_work_preview_button.clicked.connect(
            self._handle_rudolf_work_preview
        )
        self.developer_layout.addWidget(
            self.rudolf_work_preview_button
        )
        self.rudolf_work_preview_status = QLabel(
            RUDOLF_WORK_PREVIEW_IDLE_TEXT
        )
        self.rudolf_work_preview_status.setProperty(
            "tanukiRole",
            "settingsNotice",
        )
        self.rudolf_work_preview_status.setWordWrap(True)
        self.developer_layout.addWidget(
            self.rudolf_work_preview_status
        )
        self.race_preview_button = NoticeboardAction(
            "預覽魯道夫 vs 帝寶競賽"
        )
        self.race_preview_button.setProperty(
            "tanukiRole",
            "settingsAction",
        )
        self.race_preview_button.setAccessibleName(
            "預覽魯道夫與帝寶競賽"
        )
        self.race_preview_button.clicked.connect(
            self._handle_race_preview
        )
        self.developer_layout.addWidget(self.race_preview_button)
        self.race_preview_status = QLabel(RACE_PREVIEW_IDLE_TEXT)
        self.race_preview_status.setProperty(
            "tanukiRole",
            "settingsNotice",
        )
        self.race_preview_status.setWordWrap(True)
        self.developer_layout.addWidget(self.race_preview_status)
        self.chorus_preview_button = NoticeboardAction("立即預覽合奏")
        self.chorus_preview_button.setProperty(
            "tanukiRole",
            "settingsAction",
        )
        self.chorus_preview_button.setAccessibleName("立即預覽合奏")
        self.chorus_preview_button.clicked.connect(
            self._handle_chorus_preview
        )
        self.developer_layout.addWidget(self.chorus_preview_button)
        self.chorus_preview_status = QLabel(CHORUS_PREVIEW_IDLE_TEXT)
        self.chorus_preview_status.setProperty(
            "tanukiRole",
            "settingsNotice",
        )
        self.chorus_preview_status.setWordWrap(True)
        self.developer_layout.addWidget(self.chorus_preview_status)
        self.transformation_control_label = self._create_label(
            "沙盒形態控制"
        )
        self.transformation_control_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignVCenter
        )
        self.developer_layout.addWidget(
            self.transformation_control_label
        )
        self.transformation_preview_row = QHBoxLayout()
        self.transformation_preview_buttons = {}
        for pet_name, display_name in TRANSFORMATION_PREVIEW_NAMES.items():
            button = NoticeboardAction(f"手動變身{display_name}")
            button.symbol = "sparkles"
            button.setProperty("tanukiRole", "settingsAction")
            button.setAccessibleName(f"切換{display_name}變身形態")
            button.clicked.connect(
                lambda checked=False, name=pet_name: (
                    self._handle_transformation_preview(name)
                )
            )
            self.transformation_preview_row.addWidget(button)
            self.transformation_preview_buttons[pet_name] = button
        self.developer_layout.addLayout(
            self.transformation_preview_row
        )
        self.transformation_preview_status = QLabel(
            TRANSFORMATION_PREVIEW_IDLE_TEXT
        )
        self.transformation_preview_status.setProperty(
            "tanukiRole",
            "settingsNotice",
        )
        self.transformation_preview_status.setWordWrap(True)
        self.developer_layout.addWidget(
            self.transformation_preview_status
        )
        self.sleep_control_label = self._create_label("沙盒睡眠控制")
        self.developer_layout.addWidget(self.sleep_control_label)
        self.sleep_control_grid = QGridLayout()
        self.sleep_control_grid.setHorizontalSpacing(theme.spacing_sm)
        self.sleep_control_grid.setVerticalSpacing(theme.spacing_sm)
        self.sleep_control_buttons = {}
        for index, (pet_name, display_name) in enumerate(
            SLEEP_CONTROL_NAMES.items()
        ):
            button = NoticeboardAction(f"讓{display_name}睡覺")
            button.symbol = "sleep"
            button.setProperty("tanukiRole", "settingsAction")
            button.setAccessibleName(f"切換{display_name}睡眠狀態")
            button.clicked.connect(
                lambda checked=False, name=pet_name: (
                    self._handle_sleep_control(name)
                )
            )
            self.sleep_control_grid.addWidget(
                button,
                index // 3,
                index % 3,
            )
            self.sleep_control_buttons[pet_name] = button
        self.developer_layout.addLayout(self.sleep_control_grid)
        self.sleep_control_status = QLabel(SLEEP_CONTROL_IDLE_TEXT)
        self.sleep_control_status.setProperty(
            "tanukiRole",
            "settingsNotice",
        )
        self.sleep_control_status.setWordWrap(True)
        self.developer_layout.addWidget(self.sleep_control_status)
        self.validation_button = NoticeboardAction("檢查 Config / Manifest")
        self.validation_button.setProperty("tanukiRole", "settingsAction")
        self.validation_button.clicked.connect(self._handle_validation)
        self.developer_layout.addWidget(self.validation_button)

        self._compose_noticeboard_cards()

        self.settings_shell = QFrame()
        self.settings_shell.setProperty("tanukiRole", "settingsShell")

        self.settings_tab_bar = QFrame(self.settings_shell)
        self.settings_tab_bar.setProperty("tanukiRole", "settingsTabBar")
        self.settings_tab_button_group = QButtonGroup(self)
        self.settings_tab_button_group.setExclusive(True)
        self.settings_tab_buttons = {}
        for index, tab_key in enumerate(STATUS_TAB_ORDER):
            button = NoticeboardTab(
                "leaf" if tab_key == "mode" else "wrench",
                self.settings_tab_bar,
            )
            button.setCheckable(True)
            button.setProperty("tanukiRole", "settingsTabButton")
            button.setProperty("tabKey", tab_key)
            button.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )
            button.clicked.connect(
                lambda checked=False, key=tab_key: (
                    self._select_tab(key) if checked else None
                )
            )
            self.settings_tab_button_group.addButton(button, index)
            self.settings_tab_buttons[tab_key] = button
        self.settings_tab_buttons[self._active_tab_key].setChecked(True)

        self.settings_content_surface = QFrame(self.settings_shell)
        self.settings_content_surface.setProperty(
            "tanukiRole",
            "settingsPaperSurface",
        )
        self.settings_content_layout = QVBoxLayout(
            self.settings_content_surface
        )
        self.settings_content_surface.setStyleSheet("QFrame { background: transparent; border: none; }")
        self.settings_content_layout.setContentsMargins(0, 0, 0, 0)
        self.settings_content_layout.setSpacing(theme.spacing_sm)

        self.settings_scroll = QScrollArea()
        self.settings_scroll.setObjectName("tanukiStatusSettingsScroll")
        self.settings_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.settings_scroll.setWidgetResizable(True)
        self.settings_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.settings_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.settings_scroll.setAutoFillBackground(False)
        self.settings_scroll.viewport().setAutoFillBackground(False)
        self.settings_scroll.setStyleSheet(
            "QScrollArea#tanukiStatusSettingsScroll {"
            " background: transparent; border: none; }"
            "QScrollArea#tanukiStatusSettingsScroll > QWidget > QWidget {"
            " background: transparent; }"
        )
        self.settings_scroll.setWidget(self.settings_grid)
        self.settings_content_layout.addWidget(self.settings_scroll, stretch=1)
        root_layout.addWidget(self.settings_shell, stretch=1)

        self.set_binding(binding)
        self.retranslate_ui()
        self._update_responsive_layout(force=True)
        self.hover_help = SettingsHoverHelp(self)

    def set_binding(self, binding):
        binding_changed = binding is not self.binding
        if binding_changed:
            self._reset_race_preview_status()
            self._reset_chorus_preview_status()
            self._reset_transformation_preview_status()
        self.binding = binding
        if binding is None:
            self._reset_rudolf_work_preview_status()
            self._reset_race_preview_status()
            self._reset_chorus_preview_status()
        self.unavailable_label.setVisible(binding is None)
        self.settings_grid.setEnabled(binding is not None)
        self.settings_tab_bar.setEnabled(binding is not None)
        if binding is not None:
            self.refresh_from_binding(force_rebuild=binding_changed or self._option_signature is None)

    def refresh_from_binding(self, force_rebuild=False):
        if self.binding is None:
            return
        snapshot = self.binding.snapshot()
        set_ui_locale(snapshot.ui_locale)
        self.retranslate_ui()
        signature = (
            snapshot.world_mode_options,
            snapshot.time_scale_options,
            snapshot.display_scale_options,
            snapshot.teio_duration_options,
            snapshot.tsuyoshi_duration_options,
            snapshot.race_frequency_options,
            snapshot.chorus_frequency_options,
            snapshot.mood_climate_options,
            snapshot.memory_album_mode_options,
            snapshot.memory_album_capacity_options,
            snapshot.ui_locale_options,
            snapshot.ui_text_size_options,
        )
        if force_rebuild or signature != self._option_signature:
            self._rebuild_option_buttons(snapshot)
            self._option_signature = signature
        else:
            self._retranslate_option_buttons(snapshot)

        self._refreshing = True
        try:
            debug_blocker = QSignalBlocker(self.debug_switch)
            care_blocker = QSignalBlocker(self.care_switch)
            social_status_blocker = QSignalBlocker(
                self.social_status_switch
            )
            sleep_blocker = QSignalBlocker(
                self.autonomous_sleep_switch
            )
            transformation_blocker = QSignalBlocker(
                self.autonomous_transformation_switch
            )
            self.debug_switch.setChecked(snapshot.debug_enabled)
            self.care_switch.setChecked(
                snapshot.care_feature_enabled
            )
            self.social_status_switch.setChecked(
                snapshot.social_status_enabled
            )
            self.autonomous_sleep_switch.setChecked(
                snapshot.autonomous_sleep_enabled
            )
            self.autonomous_transformation_switch.setChecked(
                snapshot.autonomous_transformation_enabled
            )
            preview_enabled = snapshot.world_mode == "sandbox"
            self.rudolf_work_preview_button.setEnabled(
                preview_enabled
            )
            self.rudolf_work_preview_button.setToolTip(
                translate_ui(
                    "settings.preview_work_tooltip",
                    default=(
                        "使用 manifest 的 activity_work_stationary 與 "
                        "activity_work_rest 預覽；不套用正式結算。"
                    ),
                )
                if preview_enabled
                else translate_ui(
                    "settings.preview_work_sandbox_only",
                    default="只可在沙盒模式使用工作預覽。",
                )
            )
            self.race_preview_button.setEnabled(preview_enabled)
            self.race_preview_button.setToolTip(
                translate_ui(
                    "settings.preview_race_tooltip",
                    default=(
                        "使用競賽 manifest contexts 播放完整流程；"
                        "不寫入正式事件或數值。"
                    ),
                )
                if preview_enabled
                else translate_ui(
                    "settings.preview_race_sandbox_only",
                    default="只可在沙盒模式使用競賽預覽。",
                )
            )
            self.chorus_preview_button.setEnabled(preview_enabled)
            self.chorus_preview_button.setToolTip(
                translate_ui(
                    "settings.preview_chorus_tooltip",
                    default=(
                        "立即開始合奏並沿用自主加入／觀看反應；"
                        "不寫入事件或套用收益。"
                    ),
                )
                if preview_enabled
                else translate_ui(
                    "settings.preview_chorus_sandbox_only",
                    default="只可在沙盒模式使用合奏預覽。",
                )
            )
            transformation_states = (
                self._transformation_control_states()
            )
            transformation_presentation = (
                build_transformation_control_presentation(
                    transformation_states,
                    world_mode=snapshot.world_mode,
                )
            )
            self._apply_transformation_control_presentation(
                transformation_presentation,
                transformation_states,
            )
            self._refresh_sleep_controls(snapshot.world_mode)
            self._set_checked(
                self.world_mode_buttons,
                self._option_index(
                    snapshot.world_mode_options,
                    snapshot.world_mode,
                ),
            )
            self._set_checked(self.time_scale_buttons, snapshot.time_scale_index)
            self._set_checked(self.display_scale_buttons, snapshot.display_scale_index)
            self._set_checked(
                self.ui_text_size_buttons,
                self._option_index(snapshot.ui_text_size_options, snapshot.ui_text_size),
            )
            self._set_checked(self.teio_duration_buttons, snapshot.teio_duration_index)
            self._set_checked(self.tsuyoshi_duration_buttons, snapshot.tsuyoshi_duration_index)
            self._set_checked(
                self.race_frequency_buttons,
                self._option_index(
                    snapshot.race_frequency_options,
                    snapshot.race_frequency,
                ),
            )
            self._set_checked(
                self.chorus_frequency_buttons,
                self._option_index(
                    snapshot.chorus_frequency_options,
                    snapshot.chorus_frequency,
                ),
            )
            self._set_checked(
                self.mood_climate_buttons,
                self._option_index(
                    snapshot.mood_climate_options,
                    snapshot.mood_climate,
                ),
            )
            self._set_checked(
                self.memory_album_mode_buttons,
                self._option_index(
                    snapshot.memory_album_mode_options,
                    snapshot.memory_album_mode,
                ),
            )
            self._set_checked(
                self.memory_album_capacity_buttons,
                self._option_index(
                    snapshot.memory_album_capacity_options,
                    snapshot.memory_album_capacity,
                ),
            )
            self._set_checked(
                self.ui_locale_buttons,
                self._option_index(
                    snapshot.ui_locale_options,
                    snapshot.ui_locale,
                ),
            )
            self._apply_update_status(snapshot)
            del transformation_blocker
            del sleep_blocker
            del social_status_blocker
            del care_blocker
            del debug_blocker
        finally:
            self._refreshing = False
        self._last_settings_snapshot = snapshot

    def _rebuild_option_buttons(self, snapshot):
        for group in self._button_groups:
            group.deleteLater()
        self._button_groups = []
        self.world_mode_buttons = self._populate_selector(
            self.world_mode_row,
            snapshot.world_mode_options,
            lambda value: translate_ui(
                f"settings.world_modes.{value}",
                default=WORLD_MODE_LABELS.get(value, str(value)),
            ),
            lambda index: self._handle_world_mode(
                snapshot.world_mode_options[index]
            ),
        )
        self.time_scale_buttons = self._populate_selector(
            self.time_scale_row,
            snapshot.time_scale_options,
            lambda value: f"{value:g}x",
            self._handle_time_scale,
        )
        self.display_scale_buttons = self._populate_selector(
            self.display_scale_row,
            snapshot.display_scale_options,
            lambda value: f"{value:g}x",
            self._handle_display_scale,
        )
        self.ui_text_size_buttons = self._populate_selector(
            self.ui_text_size_row,
            snapshot.ui_text_size_options,
            lambda value: translate_ui(f"settings.text_sizes.{value}", default=value),
            lambda index: self._handle_ui_text_size(snapshot.ui_text_size_options[index]),
        )
        self.teio_duration_buttons = self._populate_selector(
            self.teio_duration_row,
            snapshot.teio_duration_options,
            lambda value: f"{value}s",
            lambda index: self._handle_social_duration("teio", index),
        )
        self.tsuyoshi_duration_buttons = self._populate_selector(
            self.tsuyoshi_duration_row,
            snapshot.tsuyoshi_duration_options,
            lambda value: f"{value}s",
            lambda index: self._handle_social_duration("tsuyoshi", index),
        )
        self.race_frequency_buttons = self._populate_selector(
            self.race_frequency_row,
            snapshot.race_frequency_options,
            lambda value: translate_ui(
                f"settings.frequencies.{value}",
                default=RACE_FREQUENCY_LABELS.get(value, str(value)),
            ),
            lambda index: self._handle_race_frequency(
                snapshot.race_frequency_options[index]
            ),
        )
        self.chorus_frequency_buttons = self._populate_selector(
            self.chorus_frequency_row,
            snapshot.chorus_frequency_options,
            lambda value: translate_ui(
                f"settings.frequencies.{value}",
                default=RACE_FREQUENCY_LABELS.get(value, str(value)),
            ),
            lambda index: self._handle_chorus_frequency(
                snapshot.chorus_frequency_options[index]
            ),
        )
        self.mood_climate_buttons = self._populate_selector(
            self.mood_climate_row,
            snapshot.mood_climate_options,
            lambda value: translate_ui(
                f"settings.mood_climates.{value}",
                default=MOOD_CLIMATE_LABELS.get(value, str(value)),
            ),
            lambda index: self._handle_mood_climate(
                snapshot.mood_climate_options[index]
            ),
        )
        self.memory_album_mode_buttons = self._populate_selector(
            self.memory_album_mode_row,
            snapshot.memory_album_mode_options,
            lambda value: translate_ui(
                f"memory_album.mode.{value}",
                default={
                    "off": "不開啟",
                    "events": "互動事件",
                    "random": "隨機拍照",
                }.get(value, str(value)),
            ),
            lambda index: self._handle_memory_album_mode(
                snapshot.memory_album_mode_options[index]
            ),
        )
        self.memory_album_capacity_buttons = self._populate_selector(
            self.memory_album_capacity_row,
            snapshot.memory_album_capacity_options,
            lambda value: str(value),
            lambda index: self._handle_memory_album_capacity(
                snapshot.memory_album_capacity_options[index]
            ),
        )
        self.ui_locale_buttons = self._populate_selector(
            self.ui_locale_row,
            snapshot.ui_locale_options,
            lambda value: translate_ui(
                "meta.language_name",
                locale=value,
                default=str(value),
            ),
            lambda index: self._handle_ui_locale(
                snapshot.ui_locale_options[index]
            ),
        )
        for value, button in zip(
            snapshot.race_frequency_options,
            self.race_frequency_buttons,
        ):
            button.setToolTip(
                translate_ui(
                    f"settings.race_frequency_tooltips.{value}",
                    default=RACE_FREQUENCY_TOOLTIPS.get(value, ""),
                )
            )
        for value, button in zip(
            snapshot.chorus_frequency_options,
            self.chorus_frequency_buttons,
        ):
            button.setToolTip(translate_ui(
                f"settings.chorus_frequency_tooltips.{value}",
                default=CHORUS_FREQUENCY_TOOLTIPS.get(value, ""),
            ))
        for value, button in zip(
            snapshot.mood_climate_options,
            self.mood_climate_buttons,
        ):
            button.setToolTip(translate_ui(
                f"settings.mood_climate_tooltips.{value}",
                default=MOOD_CLIMATE_TOOLTIPS.get(value, ""),
            ))
        self._refresh_setting_tooltips(snapshot)
        self._update_responsive_layout(force=True)
        if hasattr(self, "hover_help"):
            self.hover_help.refresh_targets()

    def _compose_noticeboard_cards(self):
        """Reuse the existing controls inside the four illustrated paper cards."""
        self.basic_card = self._create_group("")
        self.race_preview_button.symbol = "race"
        self.chorus_preview_button.symbol = "music"
        self.basic_card_layout = QVBoxLayout(self.basic_card)
        self.memory_card = self._create_group("")
        self.memory_card_layout = QVBoxLayout(self.memory_card)
        for card_layout, groups in (
            (self.basic_card_layout, (self.runtime_group, self.timing_group)),
            (self.memory_card_layout, (self.memory_group, self.locale_update_group)),
        ):
            card_layout.setContentsMargins(12, 47, 12, 12)
            card_layout.setSpacing(6)
            for group in groups:
                group.embedded = True
                group.layout().setContentsMargins(0, 0, 0, 0)
                group.layout().setVerticalSpacing(6)
                card_layout.addWidget(group)

        for group in (self.rhythm_group, self.social_group, self.developer_group):
            group.layout().setContentsMargins(12, 47, 12, 12)
            group.layout().setSpacing(6)
        self.developer_layout.setSpacing(12)
        self.memory_settings_note.hide()
        self.memory_album_mode_control.setToolTip(self.memory_settings_note.text())
        # Language names need an entire card row, especially English/Japanese.
        self.locale_update_layout.removeWidget(self.locale_label)
        self.locale_label.hide()
        self.locale_update_layout.removeWidget(self.ui_locale_control)
        self.locale_update_layout.addWidget(self.ui_locale_control, 0, 0, 1, 2)
        self.locale_update_layout.removeItem(self.update_action_row)
        self.locale_update_layout.addLayout(self.update_action_row, 1, 0)
        self.locale_update_layout.removeWidget(self.update_status_label)
        self.locale_update_layout.addWidget(self.update_status_label, 1, 1)

        labels = (
            (self.world_mode_label, "globe"),
            (self.time_scale_label, "clock"),
            (self.display_scale_label, "display"),
            (self.ui_text_size_label, "display"),
            (self.care_toggle_row._text_label, "heart"),
            (self.autonomous_sleep_toggle_row._text_label, "sleep"),
            (self.autonomous_transformation_toggle_row._text_label, "sparkles"),
            (self.race_frequency_label, "race"),
            (self.chorus_frequency_label, "music"),
            (self.mood_climate_label, "sun"),
            (self.memory_mode_label, "camera"),
            (self.memory_capacity_label, "album"),
            (self.locale_label, "globe"),
            (self.debug_toggle_row._text_label, "wrench"),
            (self.social_status_toggle_row._text_label, "globe"),
        )
        for label, symbol in labels:
            label.symbol = symbol
        for label, character in (
            (self.teio_social_label, "Tokai Teio"),
            (self.tsuyoshi_social_label, "Tsurumaru Tsuyoshi"),
        ):
            if self.assets is not None:
                spec = next((a for a in self.assets.avatar_specs if a.character_name == character), None)
                if spec is not None:
                    label.avatar = self.assets.load_avatar_pixmap(spec)
        self.social_explanation = QLabel()
        self.social_explanation.setProperty("tanukiRole", "settingsNotice")
        self.social_explanation.setWordWrap(True)
        self.social_layout.addWidget(self.social_explanation, 2, 0, 1, 2)
        self.social_layout.setRowStretch(3, 1)
        self._noticeboard_cards = (
            self.basic_card, self.rhythm_group, self.social_group,
            self.memory_card, self.developer_group,
        )

    def _position_noticeboard_surfaces(self):
        if not hasattr(self, "settings_content_surface"):
            return
        self.layout().activate()
        # Source-art coordinates relative to (90, 44, 1076, 734). Keeping the
        # same transform as the skin prevents paper and controls from drifting.
        sx = self.settings_shell.width() / 1076.0
        sy = self.settings_shell.height() / 734.0
        self.settings_tab_bar.setGeometry(0, 0, self.settings_shell.width(), round(94*sy))
        self.settings_tab_buttons["mode"].setGeometry(round(95*sx), 0, round(388*sx), round(89*sy))
        self.settings_tab_buttons["developer"].setGeometry(round(500*sx), round(12*sy), round(357*sx), round(77*sy))
        self.settings_content_surface.setGeometry(
            round(19*sx), round(132*sy), round(1034*sx), round(589*sy),
        )

    def _populate_selector(self, layout, options, formatter, handler):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        group = QButtonGroup(self)
        group.setExclusive(True)
        buttons = []
        for index, value in enumerate(options):
            button = NoticeboardOption(formatter(value))
            button.setCheckable(True)
            button.setProperty("tanukiRole", "settingsOption")
            if len(options) == 1:
                segment_position = "single"
            elif index == 0:
                segment_position = "first"
            elif index == len(options) - 1:
                segment_position = "last"
            else:
                segment_position = "middle"
            button.setProperty("segmentPosition", segment_position)
            button.setProperty("compact", bool(self._compact_layout))
            button.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )
            button.clicked.connect(lambda checked=False, i=index: handler(i))
            group.addButton(button, index)
            layout.addWidget(button, stretch=1)
            buttons.append(button)
        self._button_groups.append(group)
        return buttons

    def resizeEvent(self, event):
        self._position_noticeboard_surfaces()
        self._update_responsive_layout()
        super().resizeEvent(event)

    def showEvent(self, event):
        self._position_noticeboard_surfaces()
        self._update_responsive_layout()
        super().showEvent(event)
        if self.binding is not None:
            self.refresh_from_binding()

    def hideEvent(self, event):
        self.race_preview_poll_timer.stop()
        self._reset_chorus_preview_status()
        self.transformation_preview_poll_timer.stop()
        super().hideEvent(event)

    def _update_responsive_layout(self, force=False):
        available_width = self.width()
        parent = self.parentWidget()
        if parent is not None:
            available_width = min(
                available_width,
                parent.contentsRect().width(),
            )
        compact = available_width < COMPACT_SETTINGS_WIDTH
        art_scale = round(max(0.82, min(1.35, available_width / 861.0)), 2)
        scale_changed = art_scale != self._noticeboard_scale
        available_height = self.height()
        if parent is not None:
            available_height = min(
                available_height,
                parent.contentsRect().height(),
            )
        locale = get_ui_locale()
        single_column_threshold = (
            LOCALIZED_SINGLE_COLUMN_SETTINGS_WIDTH
            if locale in {"en_US", "ja_JP"} else
            SINGLE_COLUMN_SETTINGS_WIDTH
        )
        single_column_threshold = round(single_column_threshold * ui_text_scale())
        # Painted options report their true text width. Fall back to one column
        # when translated/scaled card contents cannot fit beside each other.
        mode_cards = (self.basic_card, self.rhythm_group, self.social_group, self.memory_card)
        if self._active_tab_key == "mode":
            needed_width = max(
                mode_cards[0].minimumSizeHint().width() + mode_cards[1].minimumSizeHint().width(),
                mode_cards[2].minimumSizeHint().width() + mode_cards[3].minimumSizeHint().width(),
            ) + self.theme.spacing_md
            single_column_threshold = max(single_column_threshold, needed_width)
        single_column = available_width < single_column_threshold
        if locale in {"en_US", "ja_JP"}:
            estimated_developer_width = (
                available_width
                if single_column else
                available_width * 0.48
            )
            sleep_control_columns = (
                2 if estimated_developer_width >= 760 else 1
            )
        else:
            sleep_control_columns = 3
        layout_changed = (
            single_column != self._single_column_layout
        )
        spacing_changed = compact != self._compact_layout
        sleep_grid_changed = (
            sleep_control_columns != self._sleep_control_columns
        )
        if (
            not force
            and not layout_changed
            and not spacing_changed
            and not sleep_grid_changed
            and not scale_changed
        ):
            return
        if force or layout_changed:
            self._apply_settings_grid_layout(single_column)
        self._apply_setting_field_layout(
            single_column and (ui_text_scale() > 1.0 or locale in {"en_US", "ja_JP"})
        )
        if force or sleep_grid_changed:
            self._apply_sleep_control_grid(sleep_control_columns)
        self._compact_layout = compact
        self._single_column_layout = single_column
        self._sleep_control_columns = sleep_control_columns
        if scale_changed or force:
            self._apply_noticeboard_scale(art_scale)
        self._update_tab_copy()
        horizontal_spacing = (
            self.theme.spacing_xs
            if compact else
            self.theme.spacing_sm
        )
        self.grid_layout.setHorizontalSpacing(
            0
            if single_column else
            self.theme.spacing_md
        )
        self.timing_layout.setHorizontalSpacing(horizontal_spacing)
        self.runtime_layout.setHorizontalSpacing(horizontal_spacing)
        self.social_layout.setHorizontalSpacing(horizontal_spacing)
        self.rhythm_layout.setHorizontalSpacing(horizontal_spacing)
        self.memory_layout.setHorizontalSpacing(horizontal_spacing)
        self.locale_update_layout.setHorizontalSpacing(
            horizontal_spacing
        )
        for selector_layout in (
            self.world_mode_row,
            self.time_scale_row,
            self.display_scale_row,
            self.teio_duration_row,
            self.tsuyoshi_duration_row,
            self.race_frequency_row,
            self.chorus_frequency_row,
            self.mood_climate_row,
            self.memory_album_mode_row,
            self.memory_album_capacity_row,
            self.ui_locale_row,
            self.ui_text_size_row,
        ):
            selector_layout.setSpacing(0)
        for button in (
            self.world_mode_buttons
            + self.time_scale_buttons
            + self.display_scale_buttons
            + self.teio_duration_buttons
            + self.tsuyoshi_duration_buttons
            + self.race_frequency_buttons
            + self.chorus_frequency_buttons
            + self.mood_climate_buttons
            + self.memory_album_mode_buttons
            + self.memory_album_capacity_buttons
            + self.ui_locale_buttons
            + self.ui_text_size_buttons
        ):
            button.setProperty("compact", compact)
            button.style().unpolish(button)
            button.style().polish(button)

    def _apply_noticeboard_scale(self, scale):
        self._noticeboard_scale = scale
        for label in self.findChildren(NoticeboardLabel):
            label.art_scale = scale
            label.setContentsMargins(round(28*scale), 0, 0, 0)
            label.setStyleSheet(f"color: #59351e; font-size: {ui_font_pixels(max(12, round(14*scale)))}px; font-weight: 600;")
            label.update()
        for button in self.findChildren(NoticeboardOption):
            button.art_scale = scale
            button.setFixedHeight(max(round(30*scale), ui_font_pixels(14*scale) + 14))
            button.updateGeometry()
            button.update()
        for card in self._noticeboard_cards:
            card.art_scale = scale
            card.layout().setContentsMargins(round(12*scale), round(47*scale*max(1.0, ui_text_scale())), round(12*scale), round(12*scale))
            card.layout().setSpacing(round(6*scale))
            card.update()
        for group in (self.runtime_group, self.timing_group, self.memory_group, self.locale_update_group):
            group.layout().setVerticalSpacing(round(6*scale))
        for toggle in (self.care_switch, self.autonomous_sleep_switch, self.autonomous_transformation_switch, self.debug_switch, self.social_status_switch):
            toggle.setFixedSize(round(50*scale), round(28*scale))
        self.grid_layout.setVerticalSpacing(round(10*scale))

    def refresh_ui_text_size(self):
        if hasattr(self, "hover_help"):
            self.hover_help.hide_help()
            self.hover_help.refresh_style()
        self._update_responsive_layout(force=True)

    def _apply_setting_field_layout(self, stacked):
        """Give long labels and options separate rows before shrinking text."""
        for layout, first_row, fields in (
            (self.runtime_layout, 0, ((self.world_mode_label, self.world_mode_control),)),
            (self.timing_layout, 0, (
                (self.time_scale_label, self.time_scale_control),
                (self.display_scale_label, self.display_scale_control),
                (self.ui_text_size_label, self.ui_text_size_control),
            )),
            (self.rhythm_layout, 2, (
                (self.race_frequency_label, self.race_frequency_control),
                (self.chorus_frequency_label, self.chorus_frequency_control),
                (self.mood_climate_label, self.mood_climate_control),
            )),
            (self.social_layout, 0, (
                (self.teio_social_label, self.teio_duration_control),
                (self.tsuyoshi_social_label, self.tsuyoshi_duration_control),
            )),
            (self.memory_layout, 0, (
                (self.memory_mode_label, self.memory_album_mode_control),
                (self.memory_capacity_label, self.memory_album_capacity_control),
            )),
        ):
            for index, (label, control) in enumerate(fields):
                layout.removeWidget(label)
                layout.removeWidget(control)
                row = first_row + index * (2 if stacked else 1)
                if stacked:
                    layout.addWidget(label, row, 0, 1, 2)
                    layout.addWidget(control, row + 1, 0, 1, 2)
                else:
                    layout.addWidget(label, row, 0)
                    layout.addWidget(control, row, 1)
        self.runtime_layout.removeWidget(self.care_toggle_row)
        self.runtime_layout.addWidget(self.care_toggle_row, 2 if stacked else 1, 0, 1, 2)
        self.social_layout.removeWidget(self.social_explanation)
        self.social_layout.addWidget(self.social_explanation, 4 if stacked else 2, 0, 1, 2)
        for row in range(6):
            self.social_layout.setRowStretch(row, 0)
        self.social_layout.setRowStretch(5 if stacked else 3, 1)

    def _apply_sleep_control_grid(self, columns):
        columns = max(1, int(columns))
        while self.sleep_control_grid.count():
            self.sleep_control_grid.takeAt(0)
        for index, pet_name in enumerate(SLEEP_CONTROL_NAMES):
            self.sleep_control_grid.addWidget(
                self.sleep_control_buttons[pet_name],
                index // columns,
                index % columns,
            )

    def _apply_settings_grid_layout(self, single_column):
        groups = (
            self.basic_card, self.rhythm_group, self.social_group,
            self.memory_card, self.developer_group,
        )
        for group in groups:
            self.grid_layout.removeWidget(group)
            group.hide()
        for row in range(max(7, self.grid_layout.rowCount())):
            self.grid_layout.setRowStretch(row, 0)
        for column in range(max(2, self.grid_layout.columnCount())):
            self.grid_layout.setColumnStretch(column, 0)

        tab_groups = {
            "mode": (
                self.basic_card, self.rhythm_group,
                self.social_group, self.memory_card,
            ),
            "developer": (self.developer_group,),
        }
        visible_groups = tab_groups[self._active_tab_key]

        if single_column or self._active_tab_key == "developer":
            for row, group in enumerate(visible_groups):
                self.grid_layout.addWidget(group, row, 0)
            self.grid_layout.setColumnStretch(0, 1)
            self.grid_layout.setColumnStretch(1, 0)
            self.grid_layout.setRowStretch(len(visible_groups), 1)
        else:
            self.grid_layout.addWidget(self.basic_card, 0, 0)
            self.grid_layout.addWidget(self.rhythm_group, 0, 1)
            self.grid_layout.addWidget(self.social_group, 1, 0)
            self.grid_layout.addWidget(self.memory_card, 1, 1)
            self.grid_layout.setColumnStretch(0, 1)
            self.grid_layout.setColumnStretch(1, 1)
            self.grid_layout.setRowStretch(0, 5)
            self.grid_layout.setRowStretch(1, 4)
            self.grid_layout.setRowStretch(2, 0)

        # Adopt cards before showing them: a parentless first-show creates a
        # temporary native window and can steal activation from the center.
        for group in visible_groups:
            group.show()

    def _select_tab(self, tab_key):
        if tab_key not in STATUS_TAB_ORDER:
            return
        self._active_tab_key = tab_key
        button = self.settings_tab_buttons[tab_key]
        if not button.isChecked():
            button.setChecked(True)
        self._update_tab_copy()
        self._apply_settings_grid_layout(bool(self._single_column_layout))
        self.settings_scroll.verticalScrollBar().setValue(0)

    def _tab_label(self, tab_key):
        translation_key, default = STATUS_TAB_LABEL_KEYS[tab_key]
        return translate_ui(translation_key, default=default)

    def _update_tab_copy(self):
        for tab_key in STATUS_TAB_ORDER:
            label = self._tab_label(tab_key)
            button = self.settings_tab_buttons[tab_key]
            button.setText(label)
            button.setToolTip(label)
            button.setAccessibleName(label)
            button.style().unpolish(button)
            button.style().polish(button)

    def _handle_debug_toggled(self, enabled):
        if self._refreshing or self.binding is None:
            return
        self.binding.set_debug_enabled(enabled)
        self.refresh_from_binding()

    def _handle_world_mode(self, world_mode):
        if self.binding is None:
            return
        self._reset_rudolf_work_preview_status()
        self._reset_race_preview_status()
        self._reset_chorus_preview_status()
        self._reset_transformation_preview_status()
        self.binding.set_world_mode(world_mode)
        self.refresh_from_binding()

    def _handle_care_toggled(self, enabled):
        if self._refreshing or self.binding is None:
            return
        self.binding.set_care_feature_enabled(enabled)
        self.refresh_from_binding()

    def _handle_autonomous_sleep_toggled(self, enabled):
        if self._refreshing or self.binding is None:
            return
        self.binding.set_autonomous_sleep_enabled(enabled)
        self.refresh_from_binding()

    def _handle_autonomous_transformation_toggled(self, enabled):
        if self._refreshing or self.binding is None:
            return
        self.binding.set_autonomous_transformation_enabled(enabled)
        self.refresh_from_binding()

    def _handle_social_status_toggled(self, enabled):
        if self._refreshing or self.binding is None:
            return
        self.binding.set_social_status_enabled(enabled)
        self.refresh_from_binding()

    def _handle_ui_locale(self, locale):
        if self.binding is None:
            return
        set_ui_locale(locale)
        self.binding.set_ui_locale(locale)
        self.refresh_from_binding()

    def _handle_update_check(self):
        if self.binding is None:
            return
        self.binding.check_for_updates()
        self.refresh_from_binding()

    def _handle_open_update_page(self):
        if self.binding is not None:
            self.binding.open_update_page()

    def _apply_update_status(self, snapshot):
        state = str(snapshot.update_status or "idle")
        self.update_check_button.setEnabled(state != "checking")
        self.update_open_button.setVisible(
            state == "available"
            and (
                (
                    snapshot.update_package_ready
                    and bool(snapshot.update_updater_url)
                )
                or (
                    snapshot.update_method == "manual_release"
                    and bool(snapshot.update_page_url)
                )
            )
        )
        self.update_open_button.setText(translate_ui(
            "updates.download_updater"
            if snapshot.update_package_ready
            else "updates.view_release",
            default=(
                "下載更新器"
                if snapshot.update_package_ready
                else "查看 Release"
            ),
        ))
        if state == "checking":
            text = translate_ui(
                "updates.checking",
                default="正在檢查更新…",
            )
        elif state == "up_to_date":
            text = translate_ui(
                "updates.up_to_date",
                default="目前已是最新版本。",
            )
        elif state == "available":
            text = translate_ui(
                "updates.available",
                default="發現新版本 {version}。",
                version=snapshot.update_available_version,
            )
            if snapshot.update_package_ready:
                text += " " + translate_ui(
                    "updates.updater_ready",
                    default=(
                        "請到 Release 下載 TanukiUpdater.exe 後執行。"
                    ),
                )
            elif snapshot.update_method == "manual_release":
                text += " " + translate_ui(
                    "updates.manual_platform",
                    default=(
                        "此平台目前採手動更新，"
                        "請查看 Release 下載對應版本。"
                    ),
                )
            else:
                text += " " + translate_ui(
                    "updates.manual_only",
                    default=(
                        "本版本尚未提供自動更新包，"
                        "可先查看 Release。"
                    ),
                )
        elif state == "failed":
            text = translate_ui(
                "updates.failed",
                default="無法檢查更新：{reason}",
                reason=snapshot.update_error_message,
            )
        else:
            current = snapshot.update_current_version or APP_VERSION
            text = translate_ui(
                "updates.current",
                default="目前版本 {version}",
                version=current,
            )
        self.update_status_label.setText(text)

    def retranslate_ui(self):
        self.basic_card.setTitle(translate_ui("settings.noticeboard.basic", default="基本與畫面"))
        self.rhythm_group.heading = translate_ui("settings.noticeboard.activity", default="自主活動")
        self.memory_card.setTitle(translate_ui("settings.noticeboard.memory", default="回憶與系統"))
        self.unavailable_label.setText(translate_ui(
            "settings.unavailable",
            default="狀態設定尚未連接執行中的 Dashboard。",
        ))
        self.runtime_group.setTitle(translate_ui(
            "settings.groups.runtime",
            default="執行模式",
        ))
        self.timing_group.setTitle(translate_ui(
            "settings.groups.timing",
            default="時間與畫面",
        ))
        self.social_group.setTitle(translate_ui(
            "settings.groups.social_cooldown",
            default="模仿魯道夫冷卻",
        ))
        self.social_group.setToolTip(translate_ui(
            "settings.imitation_cooldown_tooltip",
            default=(
                "調整帝寶與鶴寶再次模仿魯道夫前的等待時間；"
                "不影響一般社交互動冷卻。"
            ),
        ))
        self.social_explanation.setText(self.social_group.toolTip())
        self.rhythm_group.setTitle(translate_ui(
            "settings.groups.life_rhythm",
            default="生活節奏",
        ))
        self.memory_group.setTitle(translate_ui(
            "settings.groups.memory_album",
            default="回憶相簿",
        ))
        self.developer_group.setTitle(translate_ui(
            "settings.groups.developer",
            default="開發工具",
        ))
        self._update_tab_copy()
        self.world_mode_label.setText(translate_ui(
            "settings.world_mode",
            default="世界模式",
        ))
        self.time_scale_label.setText(translate_ui(
            "settings.time_scale",
            default="時間流速",
        ))
        self.display_scale_label.setText(translate_ui(
            "settings.display_scale",
            default="顯示比例",
        ))
        self.ui_text_size_label.setText(translate_ui("settings.text_size", default="文字尺寸"))
        self.teio_social_label.setText(character_display_name("Tokai Teio"))
        self.tsuyoshi_social_label.setText(
            character_display_name("Tsurumaru Tsuyoshi")
        )
        care_text = translate_ui(
            "settings.enable_care",
            default="啟用角色照護功能",
        )
        self.care_toggle_row._text_label.setText(translate_ui("settings.noticeboard.care", default="角色照護"))
        self.care_switch.setAccessibleName(care_text)
        self.care_switch.setToolTip(translate_ui(
            "settings.enable_care_tooltip",
            default="允許低心情照護與相關家庭互動。",
        ))
        sleep_text = translate_ui(
            "settings.enable_autonomous_sleep",
            default="啟用自主睡眠",
        )
        self.autonomous_sleep_toggle_row._text_label.setText(translate_ui("settings.noticeboard.sleep", default="自主睡眠"))
        self.autonomous_sleep_switch.setAccessibleName(sleep_text)
        self.autonomous_sleep_switch.setToolTip(translate_ui(
            "settings.enable_autonomous_sleep_tooltip",
            default="關閉後不再開始新的自主睡眠；既有睡眠會正常結束。",
        ))
        transformation_text = translate_ui(
            "settings.enable_autonomous_transformation",
            default="啟用自主變身",
        )
        self.autonomous_transformation_toggle_row._text_label.setText(
            translate_ui("settings.noticeboard.transformation", default="自主變身")
        )
        self.autonomous_transformation_switch.setAccessibleName(
            transformation_text
        )
        self.autonomous_transformation_switch.setToolTip(translate_ui(
            "settings.enable_autonomous_transformation_tooltip",
            default=(
                "關閉後不再開始新的自主變身；"
                "既有變身與解除流程會正常完成。"
            ),
        ))
        self.race_frequency_label.setText(translate_ui(
            "settings.race_frequency",
            default="競賽頻率",
        ))
        self.race_frequency_label.setToolTip(translate_ui(
            "settings.race_frequency_tooltip",
            default="調整自主競賽的等待與冷卻時間；不略過資格、距離或接受判定。",
        ))
        self.chorus_frequency_label.setText(translate_ui(
            "settings.chorus_frequency",
            default="合奏頻率",
        ))
        self.chorus_frequency_label.setToolTip(translate_ui(
            "settings.chorus_frequency_tooltip",
            default="調整自主合奏的等待、重試與冷卻時間；不略過資格、距離或反應判定。",
        ))
        self.mood_climate_label.setText(translate_ui(
            "settings.mood_climate",
            default="情緒氣候",
        ))
        self.mood_climate_label.setToolTip(translate_ui(
            "settings.mood_climate_tooltip",
            default="自然心情會隨模擬倍速更新；三種氣候只調整發生率、正負傾向與幅度，不設定目標心情。",
        ))
        self.memory_mode_label.setText(translate_ui(
            "memory_album.mode.label",
            default="拍照模式",
        ))
        self.memory_capacity_label.setText(translate_ui(
            "memory_album.capacity",
            default="照片上限",
        ))
        self.memory_settings_note.setText(translate_ui(
            "memory_album.settings_note",
            default=(
                "只在 1x 自動拍攝；達到上限後停止拍攝，"
                "既有照片不會自動刪除。"
            ),
        ))
        self.memory_album_mode_control.setToolTip(self.memory_settings_note.text())
        debug_text = translate_ui(
            "settings.show_debug",
            default="顯示角色 Debug 資訊",
        )
        self.debug_toggle_row._text_label.setText(debug_text)
        self.debug_switch.setAccessibleName(debug_text)
        self.debug_switch.setToolTip(translate_ui(
            "settings.show_debug_tooltip",
            default="顯示完整角色與效能偵錯資訊。",
        ))
        social_status_text = translate_ui(
            "settings.show_social_status",
            default="顯示角色社交狀態標籤",
        )
        self.social_status_toggle_row._text_label.setText(social_status_text)
        self.social_status_switch.setAccessibleName(social_status_text)
        self.social_status_switch.setToolTip(translate_ui(
            "settings.show_social_status_tooltip",
            default="在角色頭上顯示 random、relation_watch 等行為測試標籤。",
        ))
        self.rudolf_work_preview_button.setText(translate_ui(
            "settings.preview_work",
            default="預覽魯道夫工作",
        ))
        self.race_preview_button.setText(translate_ui(
            "settings.preview_race",
            default="預覽魯道夫 vs 帝寶競賽",
        ))
        self.chorus_preview_button.setText(translate_ui(
            "settings.preview_chorus",
            default="立即預覽合奏",
        ))
        self.transformation_control_label.setText(translate_ui(
            "settings.transformation_control",
            default="沙盒形態控制",
        ))
        self.sleep_control_label.setText(translate_ui(
            "settings.sleep_control",
            default="沙盒睡眠控制",
        ))
        self.validation_button.setText(translate_ui(
            "settings.validate_config_manifest",
            default="檢查 Config / Manifest",
        ))
        if not self._waiting_for_rudolf_work_preview:
            self.rudolf_work_preview_status.setText(translate_ui(
                "settings.preview_work_idle",
                default=RUDOLF_WORK_PREVIEW_IDLE_TEXT,
            ))
        else:
            self.rudolf_work_preview_status.setText(translate_ui(
                "settings.preview_work_active",
                default=RUDOLF_WORK_PREVIEW_ACTIVE_TEXT,
            ))
        if not self._waiting_for_race_preview:
            self.race_preview_status.setText(translate_ui(
                "settings.preview_race_idle",
                default=RACE_PREVIEW_IDLE_TEXT,
            ))
        else:
            self.race_preview_status.setText(translate_ui(
                "settings.preview_race_active",
                default=RACE_PREVIEW_ACTIVE_TEXT,
            ))
        if not self._waiting_for_chorus_preview:
            self.chorus_preview_status.setText(translate_ui(
                "settings.preview_chorus_idle",
                default=CHORUS_PREVIEW_IDLE_TEXT,
            ))
        else:
            self.chorus_preview_status.setText(translate_ui(
                "settings.preview_chorus_active",
                default=CHORUS_PREVIEW_ACTIVE_TEXT,
            ))
        self.sleep_control_status.setText(
            self._sleep_control_notice_text()
        )
        self._retranslate_update_controls()
        self._refresh_setting_tooltips()
        self._update_responsive_layout(force=True)

    def _retranslate_update_controls(self):
        self.locale_update_group.setTitle(
            translate_ui(
                "settings.language_and_updates",
                default="語言與更新",
            )
        )
        self.locale_label.setText(
            translate_ui(
                "settings.interface_language",
                default="介面語言",
            )
        )
        self.update_check_button.setText(
            translate_ui(
                "updates.check_now",
                default="立即檢查更新",
            )
        )
        self.update_open_button.setText(
            translate_ui(
                "updates.download_updater",
                default="下載更新器",
            )
        )

    def _retranslate_option_buttons(self, snapshot):
        for value, button in zip(
            snapshot.world_mode_options,
            self.world_mode_buttons,
        ):
            button.setText(translate_ui(
                f"settings.world_modes.{value}",
                default=WORLD_MODE_LABELS.get(value, str(value)),
            ))
        for values, buttons in (
            (snapshot.race_frequency_options, self.race_frequency_buttons),
            (snapshot.chorus_frequency_options, self.chorus_frequency_buttons),
        ):
            for value, button in zip(values, buttons):
                button.setText(translate_ui(
                    f"settings.frequencies.{value}",
                    default=RACE_FREQUENCY_LABELS.get(value, str(value)),
                ))
        for value, button in zip(
            snapshot.race_frequency_options,
            self.race_frequency_buttons,
        ):
            button.setToolTip(translate_ui(
                f"settings.race_frequency_tooltips.{value}",
                default=RACE_FREQUENCY_TOOLTIPS.get(value, ""),
            ))
        for value, button in zip(
            snapshot.chorus_frequency_options,
            self.chorus_frequency_buttons,
        ):
            button.setToolTip(translate_ui(
                f"settings.chorus_frequency_tooltips.{value}",
                default=CHORUS_FREQUENCY_TOOLTIPS.get(value, ""),
            ))
        for value, button in zip(
            snapshot.mood_climate_options,
            self.mood_climate_buttons,
        ):
            button.setText(translate_ui(
                f"settings.mood_climates.{value}",
                default=MOOD_CLIMATE_LABELS.get(value, str(value)),
            ))
            button.setToolTip(translate_ui(
                f"settings.mood_climate_tooltips.{value}",
                default=MOOD_CLIMATE_TOOLTIPS.get(value, ""),
            ))
        for value, button in zip(
            snapshot.memory_album_mode_options,
            self.memory_album_mode_buttons,
        ):
            button.setText(translate_ui(
                f"memory_album.mode.{value}",
                default={
                    "off": "不開啟",
                    "events": "互動事件",
                    "random": "隨機拍照",
                }.get(value, str(value)),
            ))
        for value, button in zip(
            snapshot.ui_locale_options,
            self.ui_locale_buttons,
        ):
            button.setText(translate_ui(
                "meta.language_name",
                locale=value,
                default=str(value),
            ))
        for value, button in zip(snapshot.ui_text_size_options, self.ui_text_size_buttons):
            button.setText(translate_ui(f"settings.text_sizes.{value}", default=value))
        self._refresh_setting_tooltips(snapshot)

    def _refresh_setting_tooltips(self, snapshot=None):
        """Keep descriptions on the full row and on each native hit target."""
        for row, toggle in (
            (self.care_toggle_row, self.care_switch),
            (self.autonomous_sleep_toggle_row, self.autonomous_sleep_switch),
            (self.autonomous_transformation_toggle_row, self.autonomous_transformation_switch),
            (self.debug_toggle_row, self.debug_switch),
            (self.social_status_toggle_row, self.social_status_switch),
        ):
            row.setToolTip(toggle.toolTip())
            row._text_label.setToolTip(toggle.toolTip())
        for label, control, buttons, key, default in (
            (self.world_mode_label, self.world_mode_control, self.world_mode_buttons, "world_mode", "選擇世界模式；沙盒不受家庭經濟規則限制。"),
            (self.time_scale_label, self.time_scale_control, self.time_scale_buttons, "time_scale", "調整模擬時間流速；倍速期間不計成就，也不自動拍照。"),
            (self.display_scale_label, self.display_scale_control, self.display_scale_buttons, "display_scale", "調整角色顯示大小，不改變介面文字尺寸。"),
            (self.ui_text_size_label, self.ui_text_size_control, self.ui_text_size_buttons, "text_size", "調整所有介面文字尺寸：小 80%、中 100%、大 150%；初次使用預設為中，角色圖片大小不變。"),
            (self.teio_social_label, self.teio_duration_control, self.teio_duration_buttons, "imitation", self.social_group.toolTip()),
            (self.tsuyoshi_social_label, self.tsuyoshi_duration_control, self.tsuyoshi_duration_buttons, "imitation", self.social_group.toolTip()),
            (self.memory_capacity_label, self.memory_album_capacity_control, self.memory_album_capacity_buttons, "photo_capacity", "達到照片上限後停止拍攝；調低上限不會刪除已有照片。"),
            (self.locale_label, self.ui_locale_control, self.ui_locale_buttons, "language", "立即切換介面語言。"),
        ):
            text = translate_ui(f"settings.control_tooltips.{key}", default=default)
            label.setToolTip(text)
            control.setToolTip(text)
            for button in buttons:
                button.setToolTip(text)
        for label, control in (
            (self.race_frequency_label, self.race_frequency_control),
            (self.chorus_frequency_label, self.chorus_frequency_control),
            (self.mood_climate_label, self.mood_climate_control),
        ):
            control.setToolTip(label.toolTip())
        memory_text = self.memory_settings_note.text()
        self.memory_mode_label.setToolTip(memory_text)
        self.memory_album_mode_control.setToolTip(memory_text)
        modes = snapshot.memory_album_mode_options if snapshot else ("off", "events", "random")
        for value, button in zip(modes, self.memory_album_mode_buttons):
            button.setToolTip(translate_ui(f"settings.memory_mode_tooltips.{value}", default=memory_text))
        self.update_check_button.setToolTip(translate_ui(
            "settings.control_tooltips.check_updates", default="手動檢查 GitHub 上是否有新版本。"
        ))
        self.update_open_button.setToolTip(translate_ui(
            "settings.control_tooltips.download_update", default="開啟更新下載連結。"
        ))
        self.validation_button.setToolTip(translate_ui(
            "settings.control_tooltips.validate", default="檢查設定與動畫 manifest 的有效性。"
        ))

    def _handle_ui_text_size(self, value):
        if self._refreshing or self.binding is None:
            return
        self.binding.set_ui_text_size(value)
        self.refresh_from_binding()

    def _handle_time_scale(self, index):
        if self.binding is None:
            return
        self.binding.set_time_scale_index(index)
        self.refresh_from_binding()

    def _handle_display_scale(self, index):
        if self.binding is None:
            return
        self.binding.set_display_scale_index(index)
        self.refresh_from_binding()

    def _handle_social_duration(self, character_key, index):
        if self.binding is None:
            return
        self.binding.set_social_duration_index(character_key, index)
        self.refresh_from_binding()

    def _handle_race_frequency(self, value):
        if self.binding is None:
            return
        self.binding.set_race_frequency(value)
        self.refresh_from_binding()

    def _handle_chorus_frequency(self, value):
        if self.binding is None:
            return
        self.binding.set_chorus_frequency(value)
        self.refresh_from_binding()

    def _handle_mood_climate(self, value):
        if self.binding is None:
            return
        self.binding.set_mood_climate(value)
        self.refresh_from_binding()

    def _handle_memory_album_mode(self, value):
        if self.binding is None:
            return
        self.binding.set_memory_album_mode(value)
        self.refresh_from_binding()

    def _handle_memory_album_capacity(self, value):
        if self.binding is None:
            return
        self.binding.set_memory_album_capacity(value)
        self.refresh_from_binding()

    def _handle_validation(self):
        if self.binding is not None:
            self.binding.run_validation_checks()

    def _handle_rudolf_work_preview(self):
        if self.binding is None:
            return
        result = self.binding.preview_rudolf_work()
        self.rudolf_work_preview_status.setText(
            self._rudolf_work_preview_message(result)
        )
        if bool(getattr(result, "started", False)):
            self._waiting_for_rudolf_work_preview = True
            self.rudolf_work_preview_poll_timer.start()

    def _poll_rudolf_work_preview_status(self):
        if (
            not self._waiting_for_rudolf_work_preview
            or self.binding is None
        ):
            self._reset_rudolf_work_preview_status()
            return
        active_provider = getattr(
            self.binding,
            "is_rudolf_work_preview_active",
            None,
        )
        if callable(active_provider) and bool(active_provider()):
            return
        self._reset_rudolf_work_preview_status()

    def _reset_rudolf_work_preview_status(self):
        self._waiting_for_rudolf_work_preview = False
        self.rudolf_work_preview_poll_timer.stop()
        self.rudolf_work_preview_status.setText(translate_ui(
            "settings.preview_work_idle",
            default=RUDOLF_WORK_PREVIEW_IDLE_TEXT,
        ))

    def _handle_race_preview(self):
        if self.binding is None:
            return
        result = self.binding.preview_rudolf_teio_race()
        self.race_preview_status.setText(
            self._race_preview_message(result)
        )
        if bool(getattr(result, "started", False)):
            self._waiting_for_race_preview = True
            self.race_preview_poll_timer.start()

    def _poll_race_preview_status(self):
        if not self._waiting_for_race_preview or self.binding is None:
            self._reset_race_preview_status()
            return
        active_provider = getattr(
            self.binding,
            "is_race_preview_active",
            None,
        )
        if callable(active_provider) and bool(active_provider()):
            return
        self._reset_race_preview_status()

    def _reset_race_preview_status(self):
        self._waiting_for_race_preview = False
        self.race_preview_poll_timer.stop()
        self.race_preview_status.setText(translate_ui(
            "settings.preview_race_idle",
            default=RACE_PREVIEW_IDLE_TEXT,
        ))

    def _handle_chorus_preview(self):
        if self.binding is None:
            return
        result = self.binding.preview_chorus()
        self.chorus_preview_status.setText(
            self._chorus_preview_message(result)
        )
        if bool(getattr(result, "started", False)):
            self._waiting_for_chorus_preview = True
            self.chorus_preview_poll_timer.start()

    def _poll_chorus_preview_status(self):
        if not self._waiting_for_chorus_preview or self.binding is None:
            self._reset_chorus_preview_status()
            return
        active_provider = getattr(
            self.binding,
            "is_chorus_preview_active",
            None,
        )
        if callable(active_provider) and bool(active_provider()):
            return
        self._reset_chorus_preview_status()

    def _reset_chorus_preview_status(self):
        self._waiting_for_chorus_preview = False
        self.chorus_preview_poll_timer.stop()
        self.chorus_preview_status.setText(translate_ui(
            "settings.preview_chorus_idle",
            default=CHORUS_PREVIEW_IDLE_TEXT,
        ))

    def _handle_transformation_preview(self, pet_name):
        if self.binding is None:
            return
        toggle = getattr(
            self.binding,
            "toggle_transformation_preview",
            None,
        )
        result = toggle(pet_name) if callable(toggle) else None
        if (
            bool(getattr(result, "started", False))
            or bool(getattr(result, "queued", False))
        ):
            self._pending_transformation_request = (
                str(getattr(result, "character_name", "") or pet_name),
                str(getattr(result, "target_form", "") or ""),
            )
            self._transformation_notice_text = ""
            self._transformation_notice_until = 0.0
        else:
            self._set_transformation_notice(
                self._transformation_preview_message(result)
            )
        self.refresh_from_binding()

    def _handle_sleep_control(self, pet_name):
        if self.binding is None:
            return
        toggle = getattr(self.binding, "toggle_sleep_control", None)
        result = toggle(pet_name) if callable(toggle) else None
        if bool(getattr(result, "started", False)):
            outcome = "started"
        elif bool(getattr(result, "phase_changed", False)):
            outcome = "waking"
        else:
            outcome = "failure"
        self._sleep_control_notice = (
            str(pet_name or ""),
            outcome,
            str(getattr(result, "reason", "") or ""),
        )
        self.sleep_control_status.setText(
            self._sleep_control_notice_text()
        )
        self.refresh_from_binding()

    def _sleep_control_notice_text(self):
        if self._sleep_control_notice is None:
            return translate_ui(
                "settings.sleep_control_idle",
                default=SLEEP_CONTROL_IDLE_TEXT,
            )
        pet_name, outcome, reason = self._sleep_control_notice
        display_name = character_display_name(pet_name) or translate_ui(
            "common.character",
            default="角色",
        )
        if outcome == "started":
            return translate_ui(
                "sleep_control.started",
                default="{character}已開始進入睡眠。",
                character=display_name,
            )
        if outcome == "waking":
            return translate_ui(
                "sleep_control.waking",
                default="{character}已進入喚醒過場。",
                character=display_name,
            )
        defaults = {
            "sandbox_required": "睡眠控制僅可在沙盒模式使用。",
            "participant_unavailable": "找不到指定角色。",
            "participant_hidden": "角色目前未召喚，無法指定睡眠。",
            "participant_owned": "角色正在進行其他活動，暫時無法睡覺。",
            "form_blocks_sleep": "角色目前形態不允許睡眠。",
            "already_waking": "角色已在喚醒過場中。",
            "sleep_capacity_reached": "目前沒有可用的睡眠名額。",
        }
        if reason in defaults:
            return translate_ui(
                f"sleep_control.failures.{reason}",
                default=defaults[reason],
            )
        if reason:
            return translate_ui(
                "sleep_control.failures.unknown_with_reason",
                default="無法切換睡眠：{reason}",
                reason=reason,
            )
        return translate_ui(
            "sleep_control.failures.unknown",
            default="無法切換睡眠。",
        )

    def _refresh_sleep_controls(self, world_mode):
        provider = getattr(self.binding, "get_sleep_control_state", None)
        sandbox = str(world_mode or "") == "sandbox"
        for pet_name in SLEEP_CONTROL_NAMES:
            display_name = character_display_name(pet_name)
            state = (
                dict(provider(pet_name) or {})
                if callable(provider)
                else {}
            )
            button = self.sleep_control_buttons[pet_name]
            active = bool(state.get("active", False))
            phase = str(state.get("phase", "") or "")
            available = bool(state.get("available", False))
            visible = bool(state.get("visible", False))
            form_allows = bool(state.get("form_allows_sleep", False))
            if active and phase == "waking":
                button.setText(translate_ui("sleep_control.button_waking", default="{character}喚醒中", character=display_name))
                button.setEnabled(False)
                button.setToolTip(translate_ui("sleep_control.tooltip_waking", default="角色正在播放既有 waking 過場。"))
            elif active:
                button.setText(translate_ui("sleep_control.button_wake", default="喚醒{character}", character=display_name))
                button.setEnabled(sandbox)
                button.setToolTip(translate_ui("sleep_control.tooltip_wake", default="使用既有 waking 流程提早喚醒。"))
            elif not form_allows and available:
                button.setText(translate_ui("sleep_control.button_blocked", default="{character}無法睡眠", character=display_name))
                button.setEnabled(False)
                button.setToolTip(translate_ui("sleep_control.tooltip_blocked", default="角色目前形態不允許睡眠。"))
            else:
                button.setText(translate_ui("sleep_control.button_sleep", default="讓{character}睡覺", character=display_name))
                button.setEnabled(sandbox and available and visible)
                button.setToolTip(
                    translate_ui("sleep_control.tooltip_sleep", default="指定角色立即進入既有睡眠流程。")
                    if sandbox and available and visible
                    else translate_ui("sleep_control.tooltip_sandbox_only", default="僅可在沙盒中對已召喚角色使用。")
                )

    def _poll_transformation_preview_status(self):
        if self.binding is None:
            self._reset_transformation_preview_status()
            return
        snapshot = self.binding.snapshot()
        if snapshot != self._last_settings_snapshot:
            self.refresh_from_binding()
            return
        # Runtime polling must not hide/reinsert all settings cards: that emits
        # Leave/Enter repeatedly and prevents hover descriptions from settling.
        states = self._transformation_control_states()
        presentation = build_transformation_control_presentation(
            states, world_mode=snapshot.world_mode,
        )
        self._apply_transformation_control_presentation(presentation, states)
        self._refresh_sleep_controls(snapshot.world_mode)

    def _reset_transformation_preview_status(self):
        self.transformation_preview_poll_timer.stop()
        self._pending_transformation_request = None
        self._transformation_notice_text = ""
        self._transformation_notice_until = 0.0
        self.transformation_preview_status.setText(
            TRANSFORMATION_PREVIEW_IDLE_TEXT
        )

    def _transformation_control_states(self):
        state_provider = getattr(
            self.binding,
            "get_transformation_preview_state",
            None,
        )
        return {
            pet_name: (
                dict(state_provider(pet_name) or {})
                if callable(state_provider)
                else {}
            )
            for pet_name in TRANSFORMATION_PREVIEW_NAMES
        }

    def _apply_transformation_control_presentation(
        self,
        presentation,
        states,
    ):
        self._capture_transformation_completion(states)
        for button_presentation in presentation.buttons:
            button = self.transformation_preview_buttons[
                button_presentation.character_name
            ]
            button.setText(button_presentation.text)
            button.setEnabled(button_presentation.enabled)
            button.setToolTip(button_presentation.tooltip)

        now = time.monotonic()
        if presentation.has_active_operation:
            status_text = presentation.status_text
        elif (
            self._transformation_notice_text
            and now < self._transformation_notice_until
        ):
            status_text = self._transformation_notice_text
        else:
            self._transformation_notice_text = ""
            self._transformation_notice_until = 0.0
            status_text = presentation.status_text
        self.transformation_preview_status.setText(status_text)

        if presentation.should_poll and self.isVisible():
            if (
                self.transformation_preview_poll_timer.interval()
                != presentation.poll_interval_ms
            ):
                self.transformation_preview_poll_timer.setInterval(
                    presentation.poll_interval_ms
                )
            if not self.transformation_preview_poll_timer.isActive():
                self.transformation_preview_poll_timer.start()
        else:
            self.transformation_preview_poll_timer.stop()

    def _capture_transformation_completion(self, states):
        if self._pending_transformation_request is None:
            return
        character_name, target_form = (
            self._pending_transformation_request
        )
        state = states.get(character_name, {})
        if (
            bool(state.get("active", False))
            or bool(state.get("manual_end_requested", False))
            or str(state.get("current_form", "") or "") != target_form
        ):
            return
        self._pending_transformation_request = None
        self._set_transformation_notice(
            build_transformation_completion_text(
                character_name,
                target_form,
            )
        )

    def _set_transformation_notice(self, text, duration_seconds=2.5):
        self._transformation_notice_text = str(text or "")
        self._transformation_notice_until = (
            time.monotonic() + float(duration_seconds)
        )

    @staticmethod
    def _transformation_preview_message(result):
        if result is None:
            return translate_ui(
                "preview_messages.runtime_or_sandbox",
                default="無法預覽：請先切換至沙盒模式，或 Runtime 尚未連接。",
            )
        character_name = str(
            getattr(result, "character_name", "") or ""
        )
        name = character_display_name(character_name) or translate_ui(
            "common.character",
            default="角色",
        )
        if bool(getattr(result, "started", False)):
            target_form = str(
                getattr(result, "target_form", "") or ""
            )
            action = translate_ui(
                "transformation.action_revert_label"
                if target_form == "base" else
                "transformation.action_transform_label",
                default="解除變身" if target_form == "base" else "變身",
            )
            return translate_ui(
                "preview_messages.transformation_started",
                default="{character}{action}過場已開始。",
                character=name,
                action=action,
            )
        if bool(getattr(result, "queued", False)):
            return translate_ui(
                "preview_messages.transformation_queued",
                default=(
                    "{character}解除變身已排入等待；"
                    "回到地面且空閒後會自動安全解除。"
                ),
                character=name,
            )
        reason = str(getattr(result, "reason", "") or "")
        defaults = {
            "preview_requires_sandbox": "無法預覽：請先切換至沙盒模式。",
            "transition_active": "無法預覽：角色正在切換形態。",
            "participant_unavailable": "無法預覽：找不到指定角色。",
            "participant_disabled": "無法預覽：角色目前已停用。",
            "participant_hidden": "無法預覽：角色目前未顯示。",
            "participant_owned": "無法預覽：角色正在執行 Activity。",
            "participant_dragging": "無法預覽：角色正在被拖曳。",
            "participant_offer_busy": "無法預覽：角色正在進行道具互動。",
            "participant_care_busy": "無法預覽：角色正在照護或被照護。",
            "participant_social_busy": "無法預覽：角色正在進行社交互動。",
            "participant_recovering": "無法預覽：角色正在恢復或鎖定狀態。",
            "airborne": "無法預覽：角色必須先回到地面。",
            "asset_directory_missing": "無法預覽：找不到變身素材資料夾。",
            "capability_unavailable_random": "無法預覽：manifest 缺少可用的 random 素材。",
        }
        lookup_key = reason.replace(":", "_")
        if lookup_key in defaults:
            return translate_ui(
                f"preview_messages.transformation_failures.{lookup_key}",
                default=defaults[lookup_key],
            )
        if reason.startswith("asset_load_failed:"):
            return translate_ui(
                "preview_messages.transformation_failures.asset_load_failed",
                default="無法預覽：變身素材載入失敗。",
            )
        return StatusSettingsPanel._unknown_preview_message(reason)

    @staticmethod
    def _rudolf_work_preview_message(result):
        if result is None:
            return translate_ui(
                "preview_messages.runtime_unavailable",
                default="無法預覽：執行中的 Runtime 尚未連接。",
            )
        if bool(getattr(result, "started", False)):
            return translate_ui(
                "settings.preview_work_active",
                default=RUDOLF_WORK_PREVIEW_ACTIVE_TEXT,
            )

        reason = str(getattr(result, "reason", "") or "")
        rudolf = character_display_name("Symboli Rudolf")
        defaults = {
            "preview_requires_sandbox": "無法預覽：請先切換至沙盒模式。",
            "severe_mood": "無法預覽：{character}心情為 severe，沒有符合 band 的工作素材。",
            "rudolf_unavailable": "無法預覽：找不到{character}角色。",
            "participant_owned": "無法預覽：{character}正在執行其他 Activity。",
            "participant_hidden": "無法預覽：{character}目前未顯示。",
            "participant_disabled": "無法預覽：{character}目前已停用。",
            "settlement_pending": "無法預覽：正式工作的結算仍在等待完成。",
        }
        if reason in defaults:
            return translate_ui(
                f"preview_messages.work_failures.{reason}",
                default=defaults[reason],
                character=rudolf,
            )
        if reason.startswith("participant_busy:"):
            return translate_ui(
                "preview_messages.work_failures.participant_busy",
                default="無法預覽：{character}目前正在進行其他互動。",
                character=rudolf,
            )
        if reason.startswith("capability_unavailable:"):
            return translate_ui(
                "preview_messages.work_failures.capability_unavailable",
                default="無法預覽：manifest 中沒有符合目前狀態的工作素材。",
            )
        return StatusSettingsPanel._unknown_preview_message(
            reason,
            empty_key="preview_messages.work_not_started",
            empty_default="無法預覽：Runtime 未啟動工作 Activity。",
        )

    @staticmethod
    def _race_preview_message(result):
        if result is None:
            return translate_ui(
                "preview_messages.runtime_or_sandbox",
                default="無法預覽：請先切換至沙盒模式，或 Runtime 尚未連接。",
            )
        if bool(getattr(result, "started", False)):
            return translate_ui(
                "settings.preview_race_active",
                default=RACE_PREVIEW_ACTIVE_TEXT,
            )
        reason = str(getattr(result, "reason", "") or "")
        participant_name = ""
        if ":" in reason and not reason.startswith(
            ("participant_busy:", "capability_unavailable:")
        ):
            participant_name, reason = reason.split(":", 1)
        display_name = (
            character_display_name(participant_name)
            if participant_name else
            translate_ui("common.character", default="角色")
        )
        defaults = {
            "preview_requires_sandbox": "無法預覽：請先切換至沙盒模式。",
            "participant_unavailable": "無法預覽：找不到{rudolf}或{teio}。",
            "participant_hidden": "無法預覽：{character}目前未顯示。",
            "participant_disabled": "無法預覽：{character}目前已停用。",
            "participant_busy": "無法預覽：{character}正在進行其他互動。",
            "participant_airborne": "無法預覽：{character}必須先回到地面。",
            "form_blocks_race": "無法預覽：{character}目前形態不能參賽。",
            "severe_mood": "無法預覽：{character}心情為 severe。",
            "race_already_active": "無法預覽：目前已有競賽正在進行。",
            "participants_too_far": "無法預覽：{rudolf}與{teio}距離太遠，請先將兩人移近。",
            "participants_too_close": "無法預覽：{rudolf}與{teio}距離太近，請稍候兩人自然分開。",
            "race_course_unavailable": "無法預覽：目前桌面寬度不足以容納最短 500px 跑道。",
            "participant_owned": "無法預覽：參賽者正在執行其他 Activity。",
        }
        if reason in defaults:
            return translate_ui(
                f"preview_messages.race_failures.{reason}",
                default=defaults[reason],
                character=display_name,
                rudolf=character_display_name("Symboli Rudolf"),
                teio=character_display_name("Tokai Teio"),
            )
        if reason.startswith("participant_busy:"):
            return translate_ui(
                "preview_messages.race_failures.participant_busy_generic",
                default="無法預覽：參賽者正在進行其他互動。",
            )
        if reason.startswith("capability_unavailable:"):
            return translate_ui(
                "preview_messages.race_failures.capability_unavailable",
                default="無法預覽：manifest 缺少符合目前形態與 band 的競賽素材。",
            )
        return StatusSettingsPanel._unknown_preview_message(reason)

    @staticmethod
    def _chorus_preview_message(result):
        if result is None:
            return translate_ui(
                "preview_messages.runtime_or_sandbox",
                default="無法預覽：請先切換至沙盒模式，或 Runtime 尚未連接。",
            )
        if bool(getattr(result, "started", False)):
            return translate_ui(
                "settings.preview_chorus_active",
                default=CHORUS_PREVIEW_ACTIVE_TEXT,
            )
        reason = str(getattr(result, "reason", "") or "")
        defaults = {
            "preview_requires_sandbox": "無法預覽：請先切換至沙盒模式。",
            "chorus_already_active": "無法預覽：目前已有合奏正在進行。",
            "no_eligible_performer": "無法預覽：沒有可發起合奏的空閒角色或相符素材。",
            "empty_session_id": "無法預覽：無法建立合奏識別碼。",
            "perform_animation_unavailable": "無法預覽：manifest 缺少符合目前形態與 band 的演奏素材。",
        }
        if reason in defaults:
            return translate_ui(
                f"preview_messages.chorus_failures.{reason}",
                default=defaults[reason],
            )
        return StatusSettingsPanel._unknown_preview_message(reason)

    @staticmethod
    def _unknown_preview_message(
        reason,
        *,
        empty_key="preview_messages.unknown",
        empty_default="無法預覽。",
    ):
        if reason:
            return translate_ui(
                "preview_messages.unknown_with_reason",
                default="無法預覽：{reason}",
                reason=reason,
            )
        return translate_ui(empty_key, default=empty_default)

    @staticmethod
    def _set_checked(buttons, index):
        safe_index = max(0, min(len(buttons) - 1, int(index))) if buttons else -1
        for button_index, button in enumerate(buttons):
            button.setChecked(button_index == safe_index)

    @staticmethod
    def _option_index(options, selected_value):
        try:
            return tuple(options).index(selected_value)
        except ValueError:
            return 0

    def _create_group(self, title):
        group = NoticeboardSection(title, parent=self.settings_grid)
        group.setProperty("tanukiRole", "settingsGroup")
        return group

    @staticmethod
    def _create_selector_row():
        container = NoticeboardRail()
        container.setProperty("tanukiRole", "settingsSegmentedControl")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)
        return container, layout

    @staticmethod
    def _create_label(text):
        label = NoticeboardLabel(text)
        label.setProperty("tanukiRole", "settingsLabel")
        return label

    @staticmethod
    def _create_toggle_row(text, toggle):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(DEFAULT_UI_THEME.spacing_sm)
        label = NoticeboardLabel(text)
        label.setProperty("tanukiRole", "settingsToggleLabel")
        row._text_label = label
        layout.addWidget(label, stretch=1)
        layout.addWidget(toggle)
        return row
