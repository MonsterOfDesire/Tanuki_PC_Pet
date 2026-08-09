from PyQt6.QtCore import QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .information_center_spec import (
    DEFAULT_INFORMATION_CENTER_PAGE,
    INFORMATION_CENTER_PAGE_SPECS,
    PAGE_RELATION_SUMMON,
    PAGE_STATUS_SETTINGS,
    PAGE_FAMILY_STATUS,
    PAGE_EVENT_LOG,
    PAGE_ACHIEVEMENTS,
    get_information_center_page_spec,
)
from .skinned_window_frame import SkinnedWindowFrame
from .information_center_size_rules import (
    INFORMATION_CENTER_SIZE_PRESETS,
    fit_window_size_for_preset,
    get_information_center_size_preset,
)
from .information_center_state import (
    InformationCenterConfigState,
    build_information_center_config_state,
    clamp_information_center_geometry,
    normalize_information_center_config_state,
)
from .information_center_detached_ui import DetachedInformationPageWindow
from .ui_skin_assets import UiSkinAssets
from .ui_icons import create_ui_icon
from .ui_theme import DEFAULT_UI_THEME, build_ui_stylesheet
from .window_chrome import SkinnedToolWindowChrome
from .status_settings_ui import StatusSettingsPanel
from .family_summary_ui import FamilySummaryPanel
from .event_log_ui import EventLogPanel
from .relation_summon_ui import RelationSummonPanel
from .achievement_cabinet_ui import AchievementCabinetPanel


COMPACT_NAVIGATION_WIDTH = 900
NAVIGATION_ICON_NAMES = {
    PAGE_RELATION_SUMMON: "social",
    PAGE_EVENT_LOG: "story",
    PAGE_FAMILY_STATUS: "participants",
    PAGE_STATUS_SETTINGS: "system",
    PAGE_ACHIEVEMENTS: "achievement",
}


class InformationCenterPage(SkinnedWindowFrame):
    def __init__(self, assets, page_spec, parent=None, theme=DEFAULT_UI_THEME):
        super().__init__(assets, page_spec.skin_key, parent=parent, theme=theme)
        self.page_spec = page_spec

        placeholder = QWidget()
        placeholder_layout = QVBoxLayout(placeholder)
        placeholder_layout.setContentsMargins(0, 0, 0, 0)
        placeholder_layout.setSpacing(theme.spacing_sm)

        title_label = QLabel(page_spec.title)
        title_label.setProperty("tanukiRole", "pageHeading")
        placeholder_layout.addWidget(title_label)

        description_label = QLabel(page_spec.placeholder_text)
        description_label.setProperty("tanukiRole", "pagePlaceholder")
        description_label.setWordWrap(True)
        placeholder_layout.addWidget(description_label)
        placeholder_layout.addStretch(1)
        self.set_content_widget(placeholder)


class InformationCenterWindow(QWidget):
    page_changed = pyqtSignal(str)
    size_preset_applied = pyqtSignal(str)
    state_changed = pyqtSignal()

    def __init__(
        self,
        resource_resolver,
        parent=None,
        assets=None,
        theme=DEFAULT_UI_THEME,
        status_settings_binding=None,
        family_summary_binding=None,
        event_log_binding=None,
        relation_summon_binding=None,
        achievement_binding=None,
    ):
        super().__init__(parent, Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.setObjectName("tanukiInformationCenter")
        self.setWindowTitle("狸貓資訊中心")
        self.user_position_locked = False
        self._moving_programmatically = False
        self._state_change_suppressed = False
        self._current_page_id = ""
        self.resize(1120, 720)
        self.assets = assets or UiSkinAssets(resource_resolver)
        self.theme = theme
        self.pages = {}
        self.page_hosts = {}
        self.page_host_layouts = {}
        self.page_host_placeholders = {}
        self.page_indexes = {}
        self.navigation_buttons = {}
        self.size_actions = {}
        self.detached_page_windows = {}
        self.last_size_preset_id = ""
        self.status_settings_panel = None
        self.family_summary_panel = None
        self.event_log_panel = None
        self.relation_summon_panel = None
        self.achievement_cabinet_panel = None
        self._navigation_compact = None

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.navigation_frame = QFrame()
        self.navigation_frame.setObjectName("tanukiInformationNavigation")
        self.navigation_layout = QHBoxLayout(self.navigation_frame)
        self.navigation_layout.setContentsMargins(
            theme.spacing_lg,
            theme.spacing_sm,
            theme.spacing_lg,
            theme.spacing_sm,
        )
        self.navigation_layout.setSpacing(theme.spacing_sm)

        self.navigation_title = QLabel("狸貓資訊中心")
        self.navigation_title.setProperty("tanukiRole", "navigationTitle")
        self.navigation_layout.addWidget(self.navigation_title)
        self.navigation_layout.addStretch(1)

        self.size_button = QToolButton()
        self.size_button.setText("視窗尺寸")
        self.size_button.setToolTip("套用建議比例；套用後仍可拖曳視窗邊框自由調整。")
        self.size_button.setIcon(create_ui_icon("all", size=17))
        self.size_button.setIconSize(QSize(17, 17))
        self.size_button.setProperty("tanukiRole", "windowSize")
        self.size_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        size_menu = QMenu(self.size_button)
        for preset in INFORMATION_CENTER_SIZE_PRESETS:
            action = size_menu.addAction(preset.label)
            action.triggered.connect(
                lambda checked=False, preset_id=preset.preset_id: self.apply_size_preset(preset_id)
            )
            self.size_actions[preset.preset_id] = action
        self.size_button.setMenu(size_menu)

        self.detach_button = QToolButton()
        self.detach_button.setText("分離頁面")
        self.detach_button.setToolTip("將目前分頁移到可獨立操作的視窗")
        self.detach_button.setAccessibleName("分離目前分頁")
        self.detach_button.setIcon(create_ui_icon("detach", size=17))
        self.detach_button.setIconSize(QSize(17, 17))
        self.detach_button.setProperty("tanukiRole", "windowAction")
        self.detach_button.clicked.connect(self.detach_current_page)

        self.navigation_group = QButtonGroup(self)
        self.navigation_group.setExclusive(True)
        for page_spec in INFORMATION_CENTER_PAGE_SPECS:
            button = QPushButton(page_spec.navigation_label)
            button.setCheckable(True)
            button.setProperty("tanukiRole", "navigation")
            button.setProperty("pageAccent", page_spec.page_id)
            button.setIcon(
                create_ui_icon(
                    NAVIGATION_ICON_NAMES[page_spec.page_id],
                    size=17,
                )
            )
            button.setIconSize(QSize(17, 17))
            button.setToolTip(page_spec.navigation_label)
            button.clicked.connect(
                lambda checked=False, page_id=page_spec.page_id: self.select_page(page_id)
            )
            self.navigation_group.addButton(button)
            self.navigation_buttons[page_spec.page_id] = button
            self.navigation_layout.addWidget(button)
        self.navigation_layout.addWidget(self.detach_button)
        self.navigation_layout.addWidget(self.size_button)
        self.window_chrome = SkinnedToolWindowChrome(
            self,
            drag_widgets=(self.navigation_frame, self.navigation_title),
            controls_variant="dark",
        )
        self.navigation_layout.addWidget(self.window_chrome.controls)
        root_layout.addWidget(self.navigation_frame)

        self.page_stack = QStackedWidget()
        self.page_stack.setObjectName("tanukiInformationPageStack")
        for index, page_spec in enumerate(INFORMATION_CENTER_PAGE_SPECS):
            page = InformationCenterPage(self.assets, page_spec, theme=theme)
            if page_spec.page_id == PAGE_RELATION_SUMMON:
                page.set_content_margins(
                    theme.spacing_sm,
                    theme.spacing_sm,
                    theme.spacing_sm,
                    theme.spacing_sm,
                )
                self.relation_summon_panel = RelationSummonPanel(
                    self.assets,
                    relation_summon_binding,
                    theme=theme,
                )
                page.set_content_widget(self.relation_summon_panel)
            elif page_spec.page_id == PAGE_STATUS_SETTINGS:
                self.status_settings_panel = StatusSettingsPanel(
                    status_settings_binding,
                    theme=theme,
                )
                page.set_content_widget(self.status_settings_panel)
            elif page_spec.page_id == PAGE_FAMILY_STATUS:
                self.family_summary_panel = FamilySummaryPanel(
                    family_summary_binding,
                    theme=theme,
                    assets=self.assets,
                )
                page.set_content_widget(self.family_summary_panel)
            elif page_spec.page_id == PAGE_EVENT_LOG:
                self.event_log_panel = EventLogPanel(
                    event_log_binding,
                    theme=theme,
                )
                page.set_content_widget(self.event_log_panel)
            elif page_spec.page_id == PAGE_ACHIEVEMENTS:
                page.set_content_margins(
                    theme.spacing_sm,
                    theme.spacing_sm,
                    theme.spacing_sm,
                    theme.spacing_sm,
                )
                self.achievement_cabinet_panel = AchievementCabinetPanel(
                    resource_resolver,
                    binding=achievement_binding,
                    theme=theme,
                )
                page.set_content_widget(self.achievement_cabinet_panel)
            self.pages[page_spec.page_id] = page
            page_host = QWidget()
            page_host_layout = QVBoxLayout(page_host)
            page_host_layout.setContentsMargins(0, 0, 0, 0)
            page_host_layout.setSpacing(0)
            page_host_placeholder = QLabel(
                "此頁已分離。\n點擊上方分頁可喚回獨立視窗。"
            )
            page_host_placeholder.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )
            page_host_placeholder.setProperty(
                "tanukiRole",
                "pagePlaceholder",
            )
            page_host_placeholder.hide()
            page_host_layout.addWidget(page_host_placeholder)
            page_host_layout.addWidget(page)
            self.page_hosts[page_spec.page_id] = page_host
            self.page_host_layouts[page_spec.page_id] = page_host_layout
            self.page_host_placeholders[
                page_spec.page_id
            ] = page_host_placeholder
            self.page_indexes[page_spec.page_id] = index
            self.page_stack.addWidget(page_host)
        root_layout.addWidget(self.page_stack, stretch=1)

        compact_page_width = max(
            page.skin_spec.minimum_window_size[0]
            for page in self.pages.values()
        )
        compact_page_height = max(
            page.skin_spec.minimum_window_size[1]
            for page in self.pages.values()
        )
        navigation_height = theme.navigation_height + theme.spacing_sm * 2
        self._compact_minimum_size = QSize(
            compact_page_width,
            compact_page_height + navigation_height,
        )
        self.setMinimumSize(self._compact_minimum_size)
        self.setStyleSheet(build_ui_stylesheet(theme))
        self.select_page(DEFAULT_INFORMATION_CENTER_PAGE)
        self._update_navigation_density()
        self.window_chrome.refresh_geometry()

    @property
    def current_page_id(self):
        return self._current_page_id

    def select_page(self, page_id):
        page_spec = get_information_center_page_spec(page_id)
        if page_spec.page_id in self.detached_page_windows:
            self._activate_detached_page(page_spec.page_id)
            self._restore_navigation_selection()
            return
        previous_page_id = self._current_page_id
        if (
            previous_page_id
            and previous_page_id in self.pages
            and previous_page_id not in self.detached_page_windows
        ):
            self.pages[previous_page_id].set_animation_active(False)

        self.page_stack.setCurrentIndex(self.page_indexes[page_spec.page_id])
        self.navigation_buttons[page_spec.page_id].setChecked(True)
        self._current_page_id = page_spec.page_id
        self.setWindowTitle(f"狸貓資訊中心 — {page_spec.navigation_label}")
        self.pages[page_spec.page_id].set_animation_active(self.isVisible())
        self._refresh_page(page_spec.page_id)
        self._update_detach_button()
        if page_spec.page_id != previous_page_id:
            self.page_changed.emit(page_spec.page_id)
            self._emit_state_changed()

    def open_page(self, page_id=None):
        target_page_id = (
            page_id
            or self.current_page_id
            or DEFAULT_INFORMATION_CENTER_PAGE
        )
        self.show()
        self.select_page(
            target_page_id
        )
        if target_page_id in self.detached_page_windows:
            return
        self.raise_()
        self.activateWindow()

    def detach_current_page(self):
        if self.current_page_id:
            self.detach_page(self.current_page_id)

    def detach_page(self, page_id):
        page_spec = get_information_center_page_spec(page_id)
        page_id = page_spec.page_id
        if page_id == PAGE_ACHIEVEMENTS:
            return None
        if page_id in self.detached_page_windows:
            self._activate_detached_page(page_id)
            return self.detached_page_windows[page_id]

        page = self.pages[page_id]
        page.set_animation_active(False)
        self.page_host_layouts[page_id].removeWidget(page)
        self.page_host_placeholders[page_id].show()
        detached_window = DetachedInformationPageWindow(
            page_spec,
            page,
            self.navigation_buttons[page_id].icon(),
            initial_size=self.size(),
            theme=self.theme,
        )
        detached_window.dock_requested.connect(
            self._handle_detached_page_close
        )
        self.detached_page_windows[page_id] = detached_window
        self._set_navigation_detached(page_id, True)

        if self.current_page_id == page_id:
            fallback_page_id = self._next_docked_page_id(page_id)
            if fallback_page_id:
                self.select_page(fallback_page_id)
            else:
                self.page_stack.setCurrentIndex(
                    self.page_indexes[page_id]
                )
                self.navigation_buttons[page_id].setChecked(True)
                self._update_detach_button()

        self._position_detached_window(detached_window)
        detached_window.show_page()
        return detached_window

    def dock_page(self, page_id, *, activate=False):
        page_id = get_information_center_page_spec(page_id).page_id
        detached_window = self.detached_page_windows.pop(page_id, None)
        if detached_window is None:
            return False

        page = detached_window.release_page()
        if page is not None:
            self.page_host_layouts[page_id].addWidget(page)
        self.page_host_placeholders[page_id].hide()
        self._set_navigation_detached(page_id, False)
        detached_window.hide()
        detached_window.deleteLater()

        if activate:
            self.select_page(page_id)
            if self.isVisible():
                self.raise_()
                self.activateWindow()
        elif self.current_page_id == page_id and page is not None:
            page.set_animation_active(self.isVisible())
            self._refresh_page(page_id)
        self._update_detach_button()
        return True

    def dock_all_pages(self):
        for page_id in tuple(self.detached_page_windows):
            self.dock_page(page_id, activate=False)

    def is_page_detached(self, page_id):
        page_id = get_information_center_page_spec(page_id).page_id
        return page_id in self.detached_page_windows

    def is_page_visible(self, page_id):
        page_id = get_information_center_page_spec(page_id).page_id
        detached_window = self.detached_page_windows.get(page_id)
        if detached_window is not None:
            return detached_window.isVisible()
        return (
            self.isVisible()
            and self.current_page_id == page_id
        )

    def _handle_detached_page_close(self, page_id):
        self.dock_page(page_id, activate=self.isVisible())

    def _activate_detached_page(self, page_id):
        self._refresh_page(page_id)
        if not self._has_docked_pages():
            previous_page_id = self._current_page_id
            page_spec = get_information_center_page_spec(page_id)
            self.page_stack.setCurrentIndex(self.page_indexes[page_id])
            self.navigation_buttons[page_id].setChecked(True)
            self._current_page_id = page_id
            self.setWindowTitle(
                f"狸貓資訊中心 — {page_spec.navigation_label}"
            )
            self._update_detach_button()
            if page_id != previous_page_id:
                self.page_changed.emit(page_id)
                self._emit_state_changed()
        detached_window = self.detached_page_windows.get(page_id)
        if detached_window is not None:
            detached_window.show_page()

    def _restore_navigation_selection(self):
        current_button = self.navigation_buttons.get(
            self.current_page_id
        )
        if current_button is not None:
            current_button.setChecked(True)

    def _next_docked_page_id(self, page_id):
        page_ids = [
            page_spec.page_id
            for page_spec in INFORMATION_CENTER_PAGE_SPECS
        ]
        start_index = page_ids.index(page_id)
        for offset in range(1, len(page_ids) + 1):
            candidate = page_ids[(start_index + offset) % len(page_ids)]
            if candidate not in self.detached_page_windows:
                return candidate
        return ""

    def _has_docked_pages(self):
        return len(self.detached_page_windows) < len(self.pages)

    def _position_detached_window(self, detached_window):
        stagger = max(0, len(self.detached_page_windows) - 1) * 24
        target_x = self.x() + 24 + stagger
        target_y = self.y() + 24 + stagger
        screen = (
            QGuiApplication.screenAt(self.geometry().center())
            or self.screen()
            or QGuiApplication.primaryScreen()
        )
        if screen is not None:
            available = screen.availableGeometry()
            maximum_x = (
                available.right() - detached_window.width() + 1
            )
            maximum_y = (
                available.bottom() - detached_window.height() + 1
            )
            target_x = (
                available.left()
                if maximum_x < available.left()
                else max(
                    available.left(),
                    min(target_x, maximum_x),
                )
            )
            target_y = (
                available.top()
                if maximum_y < available.top()
                else max(
                    available.top(),
                    min(target_y, maximum_y),
                )
            )
        detached_window.move(target_x, target_y)

    def _set_navigation_detached(self, page_id, detached):
        button = self.navigation_buttons[page_id]
        button.setProperty("detached", bool(detached))
        page_spec = get_information_center_page_spec(page_id)
        button.setToolTip(
            f"{page_spec.navigation_label}（已分離，點擊喚回）"
            if detached
            else page_spec.navigation_label
        )
        button.style().unpolish(button)
        button.style().polish(button)

    def _refresh_page(self, page_id):
        if page_id == PAGE_RELATION_SUMMON:
            self.refresh_relation_summon()
        elif page_id == PAGE_STATUS_SETTINGS:
            self.refresh_status_settings()
        elif page_id == PAGE_FAMILY_STATUS:
            self.refresh_family_summary()
        elif page_id == PAGE_EVENT_LOG:
            self.refresh_event_log()
        elif page_id == PAGE_ACHIEVEMENTS:
            self.refresh_achievement_cabinet()

    def apply_size_preset(self, preset_id):
        preset = get_information_center_size_preset(preset_id)
        screen = self.screen() or QGuiApplication.primaryScreen()
        if screen is None:
            available_size = (preset.scene_size[0] + 96, preset.scene_size[1] + 144)
        else:
            geometry = screen.availableGeometry()
            available_size = (geometry.width(), geometry.height())
        navigation_height = self.theme.navigation_height + self.theme.spacing_sm * 2
        target_size = fit_window_size_for_preset(
            preset,
            available_size,
            navigation_height,
            minimum_size=(self.minimumWidth(), self.minimumHeight()),
        )
        self._state_change_suppressed = True
        try:
            self.resize(*target_size)
            self._update_navigation_density()
            self.window_chrome.refresh_geometry()
        finally:
            self._state_change_suppressed = False
        self.last_size_preset_id = preset.preset_id
        self.size_preset_applied.emit(preset.preset_id)
        self._emit_state_changed()

    def capture_config_state(self):
        return build_information_center_config_state(
            x=self.x() if self.user_position_locked else None,
            y=self.y() if self.user_position_locked else None,
            width=self.width(),
            height=self.height(),
            page_id=self.current_page_id,
            size_preset_id=self.last_size_preset_id,
        )

    def restore_config_state(self, state):
        state = normalize_information_center_config_state(state)
        available = self._available_geometry_for_state(state)
        x, y, width, height = clamp_information_center_geometry(
            state,
            available,
            minimum_size=(self.minimumWidth(), self.minimumHeight()),
        )

        self._state_change_suppressed = True
        try:
            self.resize(width, height)
            if x is not None and y is not None:
                self.move(x, y)
            self.user_position_locked = state.has_saved_position
            self.last_size_preset_id = state.size_preset_id
            self.select_page(state.page_id)
            self._update_navigation_density()
            self.window_chrome.refresh_geometry()
        finally:
            self._state_change_suppressed = False

    def _available_geometry_for_state(self, state):
        screens = tuple(QGuiApplication.screens())
        selected_screen = None
        if state.has_saved_position:
            desired_geometry = QRect(
                int(state.x),
                int(state.y),
                int(state.width),
                int(state.height),
            )
            selected_screen = QGuiApplication.screenAt(
                desired_geometry.center()
            )
            if selected_screen is None and screens:
                intersecting_screens = (
                    (
                        screen.availableGeometry()
                        .intersected(desired_geometry)
                        .width()
                        * screen.availableGeometry()
                        .intersected(desired_geometry)
                        .height(),
                        screen,
                    )
                    for screen in screens
                )
                intersection_area, candidate = max(
                    intersecting_screens,
                    key=lambda item: item[0],
                )
                if intersection_area > 0:
                    selected_screen = candidate
        selected_screen = (
            selected_screen
            or self.screen()
            or QGuiApplication.primaryScreen()
        )
        if selected_screen is None:
            return (
                0,
                0,
                max(self.minimumWidth(), int(state.width)),
                max(self.minimumHeight(), int(state.height)),
            )
        geometry = selected_screen.availableGeometry()
        return (
            geometry.x(),
            geometry.y(),
            geometry.width(),
            geometry.height(),
        )

    def set_status_settings_binding(self, binding):
        self.status_settings_panel.set_binding(binding)

    def refresh_status_settings(self):
        if self.status_settings_panel is not None:
            self.status_settings_panel.refresh_from_binding()

    def set_family_summary_binding(self, binding):
        self.family_summary_panel.set_binding(binding)

    def refresh_family_summary(self):
        if self.family_summary_panel is not None:
            self.family_summary_panel.refresh_from_binding()

    def set_event_log_binding(self, binding):
        self.event_log_panel.set_binding(binding)

    def refresh_event_log(self):
        if self.event_log_panel is not None:
            self.event_log_panel.refresh_from_binding()

    def set_relation_summon_binding(self, binding):
        self.relation_summon_panel.set_binding(binding)

    def refresh_relation_summon(self):
        if self.relation_summon_panel is not None:
            self.relation_summon_panel.refresh_from_binding()

    def set_achievement_binding(self, binding):
        if self.achievement_cabinet_panel is not None:
            self.achievement_cabinet_panel.set_binding(binding)

    def refresh_achievement_cabinet(self, *, sync_world_mode=False):
        if self.achievement_cabinet_panel is not None:
            return self.achievement_cabinet_panel.refresh_from_binding(
                sync_world_mode=sync_world_mode
            )
        return False

    def move_near_anchor(self, x, y):
        self._moving_programmatically = True
        try:
            self.move(x, y)
        finally:
            self._moving_programmatically = False

    def moveEvent(self, event):
        if (
            not self._moving_programmatically
            and not self._state_change_suppressed
        ):
            self.user_position_locked = True
            self._emit_state_changed()
        super().moveEvent(event)

    def resizeEvent(self, event):
        if hasattr(self, "navigation_layout"):
            self._update_navigation_density()
        if hasattr(self, "window_chrome"):
            self.window_chrome.refresh_geometry()
        self._emit_state_changed()
        super().resizeEvent(event)

    def _emit_state_changed(self):
        if not self._state_change_suppressed:
            self.state_changed.emit()

    def _update_navigation_density(self):
        compact = self.width() < COMPACT_NAVIGATION_WIDTH
        if compact == self._navigation_compact:
            self._update_detach_button(compact)
            return
        self._navigation_compact = compact
        self.navigation_title.setVisible(not compact)
        horizontal_margin = (
            self.theme.spacing_sm
            if compact else
            self.theme.spacing_lg
        )
        self.navigation_layout.setContentsMargins(
            horizontal_margin,
            self.theme.spacing_sm,
            horizontal_margin,
            self.theme.spacing_sm,
        )
        self.navigation_layout.setSpacing(
            self.theme.spacing_xs
            if compact else
            self.theme.spacing_sm
        )
        for page_spec in INFORMATION_CENTER_PAGE_SPECS:
            button = self.navigation_buttons[page_spec.page_id]
            button.setText("" if compact else page_spec.navigation_label)
            button.setMinimumWidth(44 if compact else 0)
            button.setMaximumWidth(48 if compact else 16777215)
        self.size_button.setText("" if compact else "視窗尺寸")
        self.size_button.setMinimumWidth(44 if compact else 0)
        self.size_button.setMaximumWidth(48 if compact else 16777215)
        self._update_detach_button(compact)

    def _update_detach_button(self, compact=None):
        if not hasattr(self, "detach_button"):
            return
        compact = (
            self.width() < COMPACT_NAVIGATION_WIDTH
            if compact is None
            else bool(compact)
        )
        current_is_detached = (
            self.current_page_id in self.detached_page_windows
        )
        self.detach_button.setEnabled(
            bool(self.current_page_id)
            and not current_is_detached
            and self.current_page_id != PAGE_ACHIEVEMENTS
        )
        self.detach_button.setText("" if compact else "分離頁面")
        self.detach_button.setMinimumWidth(44 if compact else 0)
        self.detach_button.setMaximumWidth(
            48 if compact else 16777215
        )
