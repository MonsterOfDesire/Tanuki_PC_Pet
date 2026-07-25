from PyQt6.QtCore import QSignalBlocker, Qt
from PyQt6.QtWidgets import (
    QButtonGroup,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .ui_theme import DEFAULT_UI_THEME
from .ui_localization import character_display_name
from .ui_controls import ToggleSwitch


COMPACT_SETTINGS_WIDTH = 660
WORLD_MODE_LABELS = {
    "golden_legend": "黃金傳說",
    "sandbox": "沙盒",
}


class StatusSettingsPanel(QWidget):
    def __init__(self, binding=None, parent=None, theme=DEFAULT_UI_THEME):
        super().__init__(parent)
        self.binding = None
        self.theme = theme
        self._refreshing = False
        self._option_signature = None
        self.world_mode_buttons = []
        self.time_scale_buttons = []
        self.display_scale_buttons = []
        self.teio_duration_buttons = []
        self.tsuyoshi_duration_buttons = []
        self._button_groups = []
        self._compact_layout = None

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(theme.spacing_sm)

        self.unavailable_label = QLabel("狀態設定尚未連接執行中的 Dashboard。")
        self.unavailable_label.setProperty("tanukiRole", "settingsNotice")
        self.unavailable_label.setWordWrap(True)
        root_layout.addWidget(self.unavailable_label)

        self.settings_grid = QWidget()
        self.grid_layout = QGridLayout(self.settings_grid)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setHorizontalSpacing(theme.spacing_md)
        self.grid_layout.setVerticalSpacing(theme.spacing_sm)

        self.runtime_group = self._create_group("執行模式")
        self.runtime_layout = QGridLayout(self.runtime_group)
        self.runtime_layout.setHorizontalSpacing(theme.spacing_sm)
        self.runtime_layout.setVerticalSpacing(theme.spacing_sm)
        self.runtime_layout.addWidget(
            self._create_label("世界模式"),
            0,
            0,
        )
        self.world_mode_row = QHBoxLayout()
        self.runtime_layout.addLayout(self.world_mode_row, 0, 1)
        self.care_switch = ToggleSwitch()
        self.care_switch.setAccessibleName("啟用角色照護功能")
        self.care_switch.setToolTip(
            "允許低心情照護與相關家庭互動。"
        )
        self.care_switch.toggled.connect(self._handle_care_toggled)
        self.runtime_layout.addWidget(
            self._create_toggle_row(
                "啟用角色照護功能",
                self.care_switch,
            ),
            1,
            0,
            1,
            2,
        )

        self.timing_group = self._create_group("時間與畫面")
        self.timing_layout = QGridLayout(self.timing_group)
        self.timing_layout.setHorizontalSpacing(theme.spacing_sm)
        self.timing_layout.setVerticalSpacing(theme.spacing_sm)
        self.timing_layout.addWidget(self._create_label("時間流速"), 0, 0)
        self.time_scale_row = QHBoxLayout()
        self.timing_layout.addLayout(self.time_scale_row, 0, 1)
        self.timing_layout.addWidget(self._create_label("顯示比例"), 1, 0)
        self.display_scale_row = QHBoxLayout()
        self.timing_layout.addLayout(self.display_scale_row, 1, 1)

        self.social_group = self._create_group("社交冷卻")
        self.social_layout = QGridLayout(self.social_group)
        self.social_layout.setHorizontalSpacing(theme.spacing_sm)
        self.social_layout.setVerticalSpacing(theme.spacing_sm)
        self.social_layout.addWidget(
            self._create_label(character_display_name("Tokai Teio")),
            0,
            0,
        )
        self.teio_duration_row = QHBoxLayout()
        self.social_layout.addLayout(self.teio_duration_row, 0, 1)
        self.social_layout.addWidget(
            self._create_label(character_display_name("Tsurumaru Tsuyoshi")),
            1,
            0,
        )
        self.tsuyoshi_duration_row = QHBoxLayout()
        self.social_layout.addLayout(self.tsuyoshi_duration_row, 1, 1)

        self.developer_group = self._create_group("開發工具")
        self.developer_layout = QVBoxLayout(self.developer_group)
        self.developer_layout.setSpacing(theme.spacing_sm)
        self.debug_switch = ToggleSwitch()
        self.debug_switch.setAccessibleName("顯示角色 Debug 資訊")
        self.debug_switch.setToolTip("顯示完整角色與效能偵錯資訊。")
        self.debug_switch.toggled.connect(self._handle_debug_toggled)
        self.developer_layout.addWidget(
            self._create_toggle_row(
                "顯示角色 Debug 資訊",
                self.debug_switch,
            )
        )
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
        self.developer_layout.addWidget(
            self._create_toggle_row(
                "顯示角色社交狀態標籤",
                self.social_status_switch,
            )
        )
        self.validation_button = QPushButton("檢查 Config / Manifest")
        self.validation_button.setProperty("tanukiRole", "settingsAction")
        self.validation_button.clicked.connect(self._handle_validation)
        self.developer_layout.addWidget(self.validation_button)

        self.grid_layout.addWidget(self.runtime_group, 0, 0)
        self.grid_layout.addWidget(self.timing_group, 0, 1)
        self.grid_layout.addWidget(self.social_group, 1, 0)
        self.grid_layout.addWidget(self.developer_group, 1, 1)
        self.grid_layout.setColumnStretch(0, 1)
        self.grid_layout.setColumnStretch(1, 1)
        root_layout.addWidget(self.settings_grid)
        root_layout.addStretch(1)

        self.set_binding(binding)
        self._update_responsive_layout(force=True)

    def set_binding(self, binding):
        binding_changed = binding is not self.binding
        self.binding = binding
        self.unavailable_label.setVisible(binding is None)
        self.settings_grid.setEnabled(binding is not None)
        if binding is not None:
            self.refresh_from_binding(force_rebuild=binding_changed or self._option_signature is None)

    def refresh_from_binding(self, force_rebuild=False):
        if self.binding is None:
            return
        snapshot = self.binding.snapshot()
        signature = (
            snapshot.world_mode_options,
            snapshot.time_scale_options,
            snapshot.display_scale_options,
            snapshot.teio_duration_options,
            snapshot.tsuyoshi_duration_options,
        )
        if force_rebuild or signature != self._option_signature:
            self._rebuild_option_buttons(snapshot)
            self._option_signature = signature

        self._refreshing = True
        try:
            debug_blocker = QSignalBlocker(self.debug_switch)
            care_blocker = QSignalBlocker(self.care_switch)
            social_status_blocker = QSignalBlocker(
                self.social_status_switch
            )
            self.debug_switch.setChecked(snapshot.debug_enabled)
            self.care_switch.setChecked(
                snapshot.care_feature_enabled
            )
            self.social_status_switch.setChecked(
                snapshot.social_status_enabled
            )
            self._set_checked(
                self.world_mode_buttons,
                self._option_index(
                    snapshot.world_mode_options,
                    snapshot.world_mode,
                ),
            )
            self._set_checked(self.time_scale_buttons, snapshot.time_scale_index)
            self._set_checked(self.display_scale_buttons, snapshot.display_scale_index)
            self._set_checked(self.teio_duration_buttons, snapshot.teio_duration_index)
            self._set_checked(self.tsuyoshi_duration_buttons, snapshot.tsuyoshi_duration_index)
            del social_status_blocker
            del care_blocker
            del debug_blocker
        finally:
            self._refreshing = False

    def _rebuild_option_buttons(self, snapshot):
        for group in self._button_groups:
            group.deleteLater()
        self._button_groups = []
        self.world_mode_buttons = self._populate_selector(
            self.world_mode_row,
            snapshot.world_mode_options,
            lambda value: WORLD_MODE_LABELS.get(value, str(value)),
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
        self._update_responsive_layout(force=True)

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
            button = QPushButton(formatter(value))
            button.setCheckable(True)
            button.setProperty("tanukiRole", "settingsOption")
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
        self._update_responsive_layout()
        super().resizeEvent(event)

    def showEvent(self, event):
        self._update_responsive_layout()
        super().showEvent(event)

    def _update_responsive_layout(self, force=False):
        available_width = self.width()
        parent = self.parentWidget()
        if parent is not None:
            available_width = min(
                available_width,
                parent.contentsRect().width(),
            )
        compact = available_width < COMPACT_SETTINGS_WIDTH
        if compact == self._compact_layout and not force:
            return
        self._compact_layout = compact
        horizontal_spacing = (
            self.theme.spacing_xs
            if compact else
            self.theme.spacing_sm
        )
        self.grid_layout.setHorizontalSpacing(
            self.theme.spacing_sm
            if compact else
            self.theme.spacing_md
        )
        self.timing_layout.setHorizontalSpacing(horizontal_spacing)
        self.runtime_layout.setHorizontalSpacing(horizontal_spacing)
        self.social_layout.setHorizontalSpacing(horizontal_spacing)
        for selector_layout in (
            self.world_mode_row,
            self.time_scale_row,
            self.display_scale_row,
            self.teio_duration_row,
            self.tsuyoshi_duration_row,
        ):
            selector_layout.setSpacing(horizontal_spacing)
        for button in (
            self.world_mode_buttons
            + self.time_scale_buttons
            + self.display_scale_buttons
            + self.teio_duration_buttons
            + self.tsuyoshi_duration_buttons
        ):
            button.setProperty("compact", compact)
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
        self.binding.set_world_mode(world_mode)
        self.refresh_from_binding()

    def _handle_care_toggled(self, enabled):
        if self._refreshing or self.binding is None:
            return
        self.binding.set_care_feature_enabled(enabled)
        self.refresh_from_binding()

    def _handle_social_status_toggled(self, enabled):
        if self._refreshing or self.binding is None:
            return
        self.binding.set_social_status_enabled(enabled)
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

    def _handle_validation(self):
        if self.binding is not None:
            self.binding.run_validation_checks()

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

    @staticmethod
    def _create_group(title):
        group = QGroupBox(title)
        group.setProperty("tanukiRole", "settingsGroup")
        return group

    @staticmethod
    def _create_label(text):
        label = QLabel(text)
        label.setProperty("tanukiRole", "settingsLabel")
        label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return label

    @staticmethod
    def _create_toggle_row(text, toggle):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(DEFAULT_UI_THEME.spacing_sm)
        label = QLabel(text)
        label.setProperty("tanukiRole", "settingsToggleLabel")
        layout.addWidget(label, stretch=1)
        layout.addWidget(toggle)
        return row
