from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .ui_icons import create_ui_icon
from .ui_skin_assets import UiSkinAssets
from .ui_skin_spec import ASSET_DASHBOARD_SIDE_ICON
from .ui_theme import DEFAULT_UI_THEME, build_ui_stylesheet
from .ui_localization import translate_ui


EXPANDED_LAUNCHER_WIDTH = 310
COLLAPSED_LAUNCHER_WIDTH = 72
LAUNCHER_MINIMUM_HEIGHT = 460


class DashboardLauncherPanel(QWidget):
    """Compact launcher surface kept separate from the legacy Dashboard form."""

    expanded_changed = pyqtSignal(bool)
    pinned_changed = pyqtSignal(bool)

    def __init__(
        self,
        binding=None,
        resource_resolver=None,
        assets=None,
        parent=None,
        theme=DEFAULT_UI_THEME,
    ):
        super().__init__(parent)
        self.binding = binding
        self.theme = theme
        self.assets = assets
        if self.assets is None and resource_resolver is not None:
            self.assets = UiSkinAssets(resource_resolver)
        self._expanded = True
        self._pinned = False
        self.setObjectName("tanukiDashboardLauncher")
        self.setMinimumHeight(LAUNCHER_MINIMUM_HEIGHT)
        self.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Expanding,
        )
        self.setStyleSheet(build_ui_stylesheet(theme))

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.page_stack = QStackedWidget()
        self.page_stack.setObjectName("tanukiDashboardLauncherStack")
        root_layout.addWidget(self.page_stack)

        self.expanded_page = self._build_expanded_page()
        self.collapsed_page = self._build_collapsed_page()
        self.page_stack.addWidget(self.expanded_page)
        self.page_stack.addWidget(self.collapsed_page)

        self._brand_pixmap = self._load_brand_pixmap()
        self._apply_brand_pixmaps()
        self.set_expanded(True, emit_signal=False)
        self.set_pinned(False, emit_signal=False)
        self.retranslate_ui()
        self.refresh_from_binding()

    @property
    def is_expanded(self):
        return self._expanded

    @property
    def is_pinned(self):
        return self._pinned

    def set_binding(self, binding):
        self.binding = binding
        self.refresh_from_binding()

    def refresh_from_binding(self):
        connected = self.binding is not None
        for button in self._action_buttons:
            button.setEnabled(connected)
        if not connected:
            self.world_status_button.setText(
                "● " + translate_ui(
                    "launcher.disconnected",
                    default="未連接",
                )
            )
            self.time_status_button.setText("● --")
            self.care_status_button.setText("● --")
            self.notice_label.hide()
            return

        snapshot = self.binding.snapshot()
        self.world_status_button.setText(
            f"● {snapshot.world_mode_label}"
        )
        self.time_status_button.setText(
            f"● {snapshot.time_scale_label}"
        )
        self.care_status_button.setText(
            f"● {snapshot.care_label}"
        )
        self.world_status_button.setProperty(
            "statusState",
            "world",
        )
        self.time_status_button.setProperty(
            "statusState",
            "enabled",
        )
        self.care_status_button.setProperty(
            "statusState",
            "enabled" if snapshot.care_enabled else "disabled",
        )
        for button in (
            self.world_status_button,
            self.time_status_button,
            self.care_status_button,
        ):
            button.style().unpolish(button)
            button.style().polish(button)
        self.shutdown_button.setText(snapshot.shutdown_text)
        self.shutdown_button.setEnabled(snapshot.shutdown_enabled)
        self.collapsed_shutdown_button.setEnabled(
            snapshot.shutdown_enabled
        )
        self.collapsed_status_dots.setText(
            '<span style="color:#f2bf5d">●</span>'
            ' <span style="color:#79c567">●</span>'
            f' <span style="color:'
            f'{"#79c567" if snapshot.care_enabled else "#8e8175"}'
            '">●</span>'
        )
        status_tooltip = (
            f"{snapshot.world_mode_label}｜"
            f"{snapshot.time_scale_label}｜"
            f"{snapshot.care_label}"
        )
        self.collapsed_status_dots.setToolTip(status_tooltip)
        self.notice_label.setText(snapshot.status_text)
        self.notice_label.setVisible(
            snapshot.show_status and bool(snapshot.status_text)
        )

    def set_expanded(self, expanded, emit_signal=True):
        expanded = bool(expanded)
        changed = expanded != self._expanded
        self._expanded = expanded
        self.page_stack.setCurrentWidget(
            self.expanded_page if expanded else self.collapsed_page
        )
        self.setFixedWidth(
            EXPANDED_LAUNCHER_WIDTH
            if expanded
            else COLLAPSED_LAUNCHER_WIDTH
        )
        self.setProperty(
            "launcherState",
            "expanded" if expanded else "collapsed",
        )
        self.style().unpolish(self)
        self.style().polish(self)
        if changed and emit_signal:
            self.expanded_changed.emit(expanded)

    def set_pinned(self, pinned, emit_signal=True):
        pinned = bool(pinned)
        changed = pinned != self._pinned
        self._pinned = pinned
        self.pin_button.setChecked(pinned)
        self.pin_button.setProperty("pinned", pinned)
        self.pin_button.setIcon(
            create_ui_icon(
                "pin",
                color="#f2bf5d" if pinned else "#fffaf2",
                size=19,
            )
        )
        self.pin_button.style().unpolish(self.pin_button)
        self.pin_button.style().polish(self.pin_button)
        self.pin_button.setToolTip(
            translate_ui(
                "launcher.pinned_tooltip",
                default="已釘選；點擊後允許自動收合",
            )
            if pinned
            else translate_ui(
                "launcher.unpinned_tooltip",
                default="未釘選；點擊後保持展開",
            )
        )
        if changed and emit_signal:
            self.pinned_changed.emit(pinned)

    def _build_expanded_page(self):
        page = QFrame()
        page.setProperty("tanukiRole", "launcherSurface")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(
            self.theme.spacing_lg,
            self.theme.spacing_md,
            self.theme.spacing_lg,
            self.theme.spacing_lg,
        )
        layout.setSpacing(self.theme.spacing_md)

        header = QHBoxLayout()
        header.setSpacing(self.theme.spacing_sm)
        self.expanded_brand_label = QLabel()
        self.expanded_brand_label.setObjectName(
            "tanukiLauncherExpandedBrand"
        )
        self.expanded_brand_label.setFixedSize(62, 62)
        self.expanded_brand_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(self.expanded_brand_label)
        header.addSpacing(self.theme.spacing_sm)
        title_column = QVBoxLayout()
        title_column.setSpacing(1)
        self.title_label = QLabel("狸貓控制中心")
        self.title_label.setProperty("tanukiRole", "launcherTitle")
        title_column.addWidget(self.title_label)
        self.subtitle_label = QLabel("桌面生活捷徑")
        self.subtitle_label.setProperty("tanukiRole", "launcherSubtitle")
        title_column.addWidget(self.subtitle_label)
        header.addLayout(title_column, stretch=1)
        self.pin_button = QToolButton()
        self.pin_button.setCheckable(True)
        self.pin_button.setIcon(
            create_ui_icon("pin", color="#fffaf2", size=19)
        )
        self.pin_button.setIconSize(QSize(19, 19))
        self.pin_button.setProperty("tanukiRole", "launcherChrome")
        self.pin_button.setAccessibleName("釘選側邊欄")
        self.pin_button.clicked.connect(self.set_pinned)
        header.addWidget(self.pin_button)
        self.collapse_button = QToolButton()
        self.collapse_button.setText("‹")
        self.collapse_button.setProperty("tanukiRole", "launcherChrome")
        self.collapse_button.setAccessibleName("收合側邊欄")
        self.collapse_button.clicked.connect(
            lambda checked=False: self.set_expanded(False)
        )
        header.addWidget(self.collapse_button)
        layout.addLayout(header)

        self.main_actions_label = QLabel("主要功能")
        self.main_actions_label.setProperty("tanukiRole", "launcherSection")
        layout.addWidget(self.main_actions_label)

        tile_row = QHBoxLayout()
        tile_row.setSpacing(self.theme.spacing_sm)
        self.information_center_button = self._create_tile_button(
            "資訊中心",
            "all",
            primary=True,
        )
        self.information_center_button.clicked.connect(
            lambda checked=False: self._invoke("open_information_center")
        )
        tile_row.addWidget(self.information_center_button, stretch=1)
        self.offer_tray_button = self._create_tile_button(
            "飲食餐盤",
            "item",
        )
        self.offer_tray_button.clicked.connect(
            lambda checked=False: self._invoke("open_offer_tray")
        )
        tile_row.addWidget(self.offer_tray_button, stretch=1)
        layout.addLayout(tile_row)

        self.status_caption = QLabel("目前狀態")
        self.status_caption.setProperty("tanukiRole", "launcherSection")
        layout.addWidget(self.status_caption)
        status_frame = QFrame()
        status_frame.setProperty("tanukiRole", "launcherStatusPanel")
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(
            self.theme.spacing_sm,
            self.theme.spacing_sm,
            self.theme.spacing_sm,
            self.theme.spacing_sm,
        )
        status_layout.setSpacing(self.theme.spacing_xs)
        self.world_status_button = self._create_status_indicator()
        self.time_status_button = self._create_status_indicator()
        self.care_status_button = self._create_status_indicator()
        for indicator in (
            self.world_status_button,
            self.time_status_button,
            self.care_status_button,
        ):
            status_layout.addWidget(indicator, stretch=1)
        layout.addWidget(status_frame)

        self.notice_label = QLabel("")
        self.notice_label.setProperty("tanukiRole", "launcherNotice")
        self.notice_label.setWordWrap(True)
        self.notice_label.hide()
        layout.addWidget(self.notice_label)

        self.settings_button = QPushButton("狀態設定")
        self.settings_button.setIcon(
            create_ui_icon("system", color="#fffaf2", size=22)
        )
        self.settings_button.setIconSize(QSize(22, 22))
        self.settings_button.setProperty(
            "tanukiRole",
            "launcherAction",
        )
        self.settings_button.clicked.connect(
            lambda checked=False: self._invoke("open_status_settings")
        )
        layout.addWidget(self.settings_button)

        layout.addStretch(1)

        self.shutdown_button = QPushButton("關閉系統")
        self.shutdown_button.setIcon(
            create_ui_icon("power", color="#fffaf2", size=22)
        )
        self.shutdown_button.setIconSize(QSize(22, 22))
        self.shutdown_button.setProperty(
            "tanukiRole",
            "launcherShutdown",
        )
        self.shutdown_button.clicked.connect(
            lambda checked=False: self._invoke("begin_shutdown")
        )
        layout.addWidget(self.shutdown_button)

        self._action_buttons = [
            self.information_center_button,
            self.offer_tray_button,
            self.settings_button,
            self.shutdown_button,
        ]
        return page

    def _build_collapsed_page(self):
        page = QFrame()
        page.setProperty("tanukiRole", "launcherSurface")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(
            self.theme.spacing_sm,
            self.theme.spacing_sm,
            self.theme.spacing_sm,
            self.theme.spacing_md,
        )
        layout.setSpacing(self.theme.spacing_sm)

        self.collapsed_brand_label = QLabel()
        self.collapsed_brand_label.setObjectName(
            "tanukiLauncherCollapsedBrand"
        )
        self.collapsed_brand_label.setFixedSize(56, 56)
        self.collapsed_brand_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(
            self.collapsed_brand_label,
            alignment=Qt.AlignmentFlag.AlignHCenter,
        )

        self.expand_button = self._create_rail_button(
            "info",
            "展開側邊欄",
        )
        self.expand_button.setText("›")
        self.expand_button.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextOnly
        )
        self.expand_button.clicked.connect(
            lambda checked=False: self.set_expanded(True)
        )
        layout.addWidget(self.expand_button)

        self.collapsed_information_button = self._create_rail_button(
            "all",
            "開啟資訊中心",
            primary=True,
        )
        self.collapsed_information_button.clicked.connect(
            lambda checked=False: self._invoke("open_information_center")
        )
        layout.addWidget(self.collapsed_information_button)
        self.collapsed_offer_button = self._create_rail_button(
            "item",
            "開啟飲食餐盤",
        )
        self.collapsed_offer_button.clicked.connect(
            lambda checked=False: self._invoke("open_offer_tray")
        )
        layout.addWidget(self.collapsed_offer_button)

        self.collapsed_status_dots = QLabel("● ● ●")
        self.collapsed_status_dots.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.collapsed_status_dots.setProperty(
            "tanukiRole",
            "launcherRailStatus",
        )
        layout.addWidget(self.collapsed_status_dots)

        self.collapsed_settings_button = self._create_rail_button(
            "system",
            "開啟狀態設定",
        )
        self.collapsed_settings_button.clicked.connect(
            lambda checked=False: self._invoke("open_status_settings")
        )
        layout.addWidget(self.collapsed_settings_button)
        layout.addStretch(1)

        self.collapsed_shutdown_button = self._create_rail_button(
            "power",
            "關閉系統",
        )
        self.collapsed_shutdown_button.clicked.connect(
            lambda checked=False: self._invoke("begin_shutdown")
        )
        layout.addWidget(self.collapsed_shutdown_button)

        self._action_buttons.extend(
            [
                self.collapsed_information_button,
                self.collapsed_offer_button,
                self.collapsed_settings_button,
                self.collapsed_shutdown_button,
            ]
        )
        return page

    def _create_tile_button(self, text, icon_name, primary=False):
        button = QToolButton()
        button.setText(text)
        button.setIcon(
            create_ui_icon(icon_name, color="#fffaf2", size=42)
        )
        button.setIconSize(QSize(42, 42))
        button.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextUnderIcon
        )
        button.setProperty("tanukiRole", "launcherTile")
        button.setProperty("primary", primary)
        button.setMinimumHeight(112)
        button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        return button

    @staticmethod
    def _create_status_indicator():
        indicator = QLabel("● --")
        indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        indicator.setProperty("tanukiRole", "launcherStatusChip")
        return indicator

    @staticmethod
    def _create_rail_button(icon_name, tooltip, primary=False):
        button = QToolButton()
        button.setIcon(
            create_ui_icon(icon_name, color="#fffaf2", size=26)
        )
        button.setIconSize(QSize(26, 26))
        button.setFixedSize(48, 48)
        button.setToolTip(tooltip)
        button.setAccessibleName(tooltip)
        button.setProperty("tanukiRole", "launcherRailAction")
        button.setProperty("primary", primary)
        return button

    def _load_brand_pixmap(self):
        if self.assets is None:
            return QPixmap()
        return self.assets.load_pixmap(ASSET_DASHBOARD_SIDE_ICON)

    def _apply_brand_pixmaps(self):
        if self._brand_pixmap.isNull():
            self.expanded_brand_label.setText("狸")
            self.collapsed_brand_label.setText("狸")
            return
        expanded = self._brand_pixmap.scaled(
            60,
            60,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        collapsed = self._brand_pixmap.scaled(
            54,
            54,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.expanded_brand_label.setPixmap(expanded)
        self.collapsed_brand_label.setPixmap(collapsed)

    def _invoke(self, method_name):
        if self.binding is None:
            return
        getattr(self.binding, method_name)()
        self.refresh_from_binding()

    def retranslate_ui(self):
        self.title_label.setText(
            translate_ui("launcher.title", default="狸貓控制中心")
        )
        self.subtitle_label.setText(
            translate_ui("launcher.subtitle", default="桌面生活捷徑")
        )
        self.main_actions_label.setText(
            translate_ui("launcher.main_actions", default="主要功能")
        )
        self.information_center_button.setText(
            translate_ui(
                "launcher.information_center",
                default="資訊中心",
            )
        )
        self.offer_tray_button.setText(
            translate_ui("launcher.offer_tray", default="飲食餐盤")
        )
        self.status_caption.setText(
            translate_ui("launcher.current_status", default="目前狀態")
        )
        self.settings_button.setText(
            translate_ui("launcher.status_settings", default="狀態設定")
        )
        self.shutdown_button.setText(
            translate_ui("launcher.shutdown", default="關閉系統")
        )
        pin_accessible = translate_ui(
            "launcher.pin_sidebar",
            default="釘選側邊欄",
        )
        self.pin_button.setAccessibleName(pin_accessible)
        collapse_accessible = translate_ui(
            "launcher.collapse_sidebar",
            default="收合側邊欄",
        )
        self.collapse_button.setAccessibleName(collapse_accessible)
        self.collapse_button.setToolTip(collapse_accessible)
        self.set_pinned(self._pinned, emit_signal=False)
        tooltips = (
            (
                self.collapsed_information_button,
                translate_ui(
                    "launcher.open_information_center",
                    default="開啟資訊中心",
                ),
            ),
            (
                self.collapsed_offer_button,
                translate_ui(
                    "launcher.open_offer_tray",
                    default="開啟飲食餐盤",
                ),
            ),
            (
                self.collapsed_settings_button,
                translate_ui(
                    "launcher.open_status_settings",
                    default="開啟狀態設定",
                ),
            ),
            (
                self.collapsed_shutdown_button,
                translate_ui("launcher.shutdown", default="關閉系統"),
            ),
        )
        for button, tooltip in tooltips:
            button.setToolTip(tooltip)
            button.setAccessibleName(tooltip)
        self.refresh_from_binding()
