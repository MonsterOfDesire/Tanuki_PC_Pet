from __future__ import annotations

import os

from PyQt6.QtCore import QEvent, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPixmap, QRegion
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .achievement_presenter import (
    ACHIEVEMENT_TIER_ORDER,
    AchievementCabinetSnapshot,
    AchievementCardSnapshot,
    AchievementUnlockNotificationSnapshot,
)
from .ui_theme import DEFAULT_UI_THEME, build_ui_stylesheet


MODE_BUTTON_LABELS = {
    "sandbox": "沙盒成就",
    "golden_legend": "黃金傳說成就",
}


class AchievementTrophyCard(QFrame):
    highlighted = pyqtSignal(object)
    cleared = pyqtSignal()

    def __init__(self, snapshot, pixmap, parent=None):
        super().__init__(parent)
        self.snapshot = snapshot
        self.setProperty("tanukiRole", "achievementCard")
        self.setProperty("unlocked", bool(snapshot.unlocked))
        self.setAccessibleName(snapshot.accessible_name)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(140, 164)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(5)
        self.trophy_label = QLabel()
        self.trophy_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.trophy_label.setMinimumSize(112, 112)
        self.trophy_label.setPixmap(
            pixmap.scaled(
                QSize(108, 108),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.trophy_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )
        layout.addWidget(self.trophy_label, stretch=1)
        self.title_label = QLabel(snapshot.title if snapshot.unlocked else "")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setWordWrap(True)
        self.title_label.setProperty("tanukiRole", "achievementCardTitle")
        self.title_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )
        layout.addWidget(self.title_label)

    def enterEvent(self, event):
        self.highlighted.emit(self.snapshot)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.hasFocus():
            self.cleared.emit()
        super().leaveEvent(event)

    def focusInEvent(self, event):
        self.highlighted.emit(self.snapshot)
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        if not self.underMouse():
            self.cleared.emit()
        super().focusOutEvent(event)


class AchievementCabinetPanel(QWidget):
    def __init__(
        self,
        resource_resolver,
        binding=None,
        parent=None,
        theme=DEFAULT_UI_THEME,
    ):
        super().__init__(parent)
        self.resource_resolver = resource_resolver
        self.binding = binding
        self.theme = theme
        self.snapshot = AchievementCabinetSnapshot(modes=())
        self.current_world_mode = "sandbox"
        self.current_tier = "G3"
        self.card_widgets = []
        self._trophy_cache = {}
        self._last_grid_columns = 0

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(theme.spacing_sm)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(theme.spacing_xs)
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        self.mode_buttons = {}
        for world_mode in ("sandbox", "golden_legend"):
            button = QPushButton(MODE_BUTTON_LABELS[world_mode])
            button.setCheckable(True)
            button.setProperty("tanukiRole", "achievementModeTab")
            button.clicked.connect(
                lambda checked=False, mode=world_mode: self.select_mode(mode)
            )
            self.mode_group.addButton(button)
            self.mode_buttons[world_mode] = button
            filter_row.addWidget(button)
        filter_row.addSpacing(theme.spacing_sm)
        self.tier_group = QButtonGroup(self)
        self.tier_group.setExclusive(True)
        self.tier_buttons = {}
        for tier in ACHIEVEMENT_TIER_ORDER:
            button = QPushButton(tier)
            button.setCheckable(True)
            button.setProperty("tanukiRole", "achievementTierTab")
            button.clicked.connect(
                lambda checked=False, value=tier: self.select_tier(value)
            )
            self.tier_group.addButton(button)
            self.tier_buttons[tier] = button
            filter_row.addWidget(button)
        filter_row.addStretch(1)
        self.progress_label = QLabel("已取得 0 / 0")
        self.progress_label.setProperty("tanukiRole", "achievementProgress")
        filter_row.addWidget(self.progress_label)
        root_layout.addLayout(filter_row)

        body_row = QHBoxLayout()
        body_row.setSpacing(theme.spacing_sm)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_area.setProperty("tanukiRole", "achievementScroll")
        self.grid_content = QWidget()
        self.grid_content.setProperty("tanukiRole", "achievementGrid")
        self.grid_layout = QGridLayout(self.grid_content)
        self.grid_layout.setContentsMargins(2, 2, 2, 2)
        self.grid_layout.setHorizontalSpacing(theme.spacing_sm)
        self.grid_layout.setVerticalSpacing(theme.spacing_sm)
        self.grid_layout.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        self.scroll_area.setWidget(self.grid_content)
        self.scroll_area.viewport().installEventFilter(self)
        body_row.addWidget(self.scroll_area, stretch=1)

        self.detail_frame = QFrame()
        self.detail_frame.setFixedWidth(212)
        self.detail_frame.setProperty("tanukiRole", "achievementDetail")
        detail_layout = QVBoxLayout(self.detail_frame)
        detail_layout.setContentsMargins(
            theme.spacing_sm,
            theme.spacing_sm,
            theme.spacing_sm,
            theme.spacing_sm,
        )
        detail_layout.setSpacing(theme.spacing_xs)
        detail_heading = QLabel("取得紀錄")
        detail_heading.setProperty("tanukiRole", "achievementDetailHeading")
        detail_layout.addWidget(detail_heading)
        self.detail_title_label = QLabel("")
        self.detail_title_label.setWordWrap(True)
        self.detail_title_label.setProperty("tanukiRole", "achievementDetailTitle")
        detail_layout.addWidget(self.detail_title_label)
        self.detail_method_label = QLabel(
            "將游標移到已取得的獎盃上，即可查看取得方式。"
        )
        self.detail_method_label.setWordWrap(True)
        self.detail_method_label.setProperty("tanukiRole", "achievementDetailText")
        detail_layout.addWidget(self.detail_method_label)
        self.detail_time_label = QLabel("")
        self.detail_time_label.setWordWrap(True)
        self.detail_time_label.setProperty("tanukiRole", "achievementDetailTime")
        detail_layout.addWidget(self.detail_time_label)
        detail_layout.addStretch(1)
        body_row.addWidget(self.detail_frame)
        root_layout.addLayout(body_row, stretch=1)

    def set_binding(self, binding):
        self.binding = binding

    def refresh_from_binding(self, *, sync_world_mode=False):
        if self.binding is None:
            return False
        provider = getattr(self.binding, "snapshot", None)
        snapshot = provider() if callable(provider) else None
        if snapshot is None:
            return False
        initial_world_mode = None
        if sync_world_mode:
            world_mode_provider = getattr(
                self.binding,
                "runtime_world_mode",
                None,
            )
            if callable(world_mode_provider):
                initial_world_mode = world_mode_provider()
        self.set_snapshot(snapshot, initial_world_mode)
        return True

    def set_snapshot(self, snapshot, initial_world_mode=None):
        self.snapshot = snapshot or AchievementCabinetSnapshot(modes=())
        available_modes = {
            mode.world_mode for mode in self.snapshot.modes
        }
        requested_mode = str(initial_world_mode or "")
        if requested_mode in available_modes:
            self.current_world_mode = requested_mode
        elif self.current_world_mode not in available_modes:
            self.current_world_mode = (
                next(iter(available_modes), "sandbox")
            )
        self.mode_buttons[self.current_world_mode].setChecked(True)
        self.tier_buttons[self.current_tier].setChecked(True)
        self._rebuild_cards()

    def select_mode(self, world_mode):
        if self.snapshot.mode_snapshot(world_mode) is None:
            return
        self.current_world_mode = str(world_mode)
        self.mode_buttons[self.current_world_mode].setChecked(True)
        self._rebuild_cards()

    def select_tier(self, tier):
        if str(tier or "") not in ACHIEVEMENT_TIER_ORDER:
            return
        self.current_tier = str(tier)
        self.tier_buttons[self.current_tier].setChecked(True)
        self._rebuild_cards()

    def clear_detail(self):
        self.detail_title_label.setText("")
        self.detail_method_label.setText(
            "將游標移到已取得的獎盃上，即可查看取得方式。"
        )
        self.detail_time_label.setText("")

    def show_card_detail(self, card):
        if not isinstance(card, AchievementCardSnapshot) or not card.unlocked:
            self.clear_detail()
            return
        self.detail_title_label.setText(card.title)
        self.detail_method_label.setText(card.acquisition_method)
        self.detail_time_label.setText(
            f"取得時間：{card.unlocked_at_text}"
            if card.unlocked_at_text else
            ""
        )

    def eventFilter(self, watched, event):
        if watched is self.scroll_area.viewport() and event.type() in {
            QEvent.Type.Resize,
            QEvent.Type.Show,
        }:
            QTimer.singleShot(0, self._reflow_cards)
        return super().eventFilter(watched, event)

    @staticmethod
    def column_count_for_width(width):
        width = max(0, int(width))
        if width >= 780:
            return 5
        if width >= 500:
            return 3
        return 2

    def _rebuild_cards(self):
        self._clear_grid_widgets()
        mode = self.snapshot.mode_snapshot(self.current_world_mode)
        tier = mode.tier_snapshot(self.current_tier) if mode else None
        self.progress_label.setText(
            f"已取得 {mode.unlocked_count} / {mode.total_count}"
            if mode else
            "已取得 0 / 0"
        )
        cards = tier.cards if tier else ()
        for card in cards:
            pixmap = self._trophy_pixmap(card)
            widget = AchievementTrophyCard(card, pixmap)
            widget.highlighted.connect(self.show_card_detail)
            widget.cleared.connect(self.clear_detail)
            self.card_widgets.append(widget)
        self.clear_detail()
        self._last_grid_columns = 0
        self._reflow_cards()

    def _reflow_cards(self):
        if not self.card_widgets:
            return
        columns = self.column_count_for_width(
            self.scroll_area.viewport().width()
        )
        if columns == self._last_grid_columns:
            return
        while self.grid_layout.count():
            self.grid_layout.takeAt(0)
        for index, card in enumerate(self.card_widgets):
            self.grid_layout.addWidget(
                card,
                index // columns,
                index % columns,
            )
        self._last_grid_columns = columns

    def _clear_grid_widgets(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.card_widgets = []

    def _trophy_pixmap(self, card):
        cache_key = (card.image_relative_path, bool(card.unlocked))
        cached = self._trophy_cache.get(cache_key)
        if cached is not None:
            return cached
        path = os.path.normpath(
            str(self.resource_resolver(card.image_relative_path))
        )
        pixmap = _trim_transparent_bounds(QPixmap(path))
        if not card.unlocked:
            pixmap = _locked_silhouette(pixmap)
        self._trophy_cache[cache_key] = pixmap
        return pixmap


class AchievementUnlockToast(QWidget):
    def __init__(self, resource_resolver, parent=None):
        super().__init__(
            parent,
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.resource_resolver = resource_resolver
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setWindowFlag(Qt.WindowType.WindowDoesNotAcceptFocus, True)
        self.setObjectName("tanukiAchievementUnlockToast")
        self.setStyleSheet(build_ui_stylesheet(DEFAULT_UI_THEME))
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide)

        frame = QFrame(self)
        frame.setProperty("tanukiRole", "achievementToast")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 10, 14, 10)
        layout.setSpacing(10)
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(58, 58)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon_label)
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        self.heading_label = QLabel()
        self.heading_label.setProperty("tanukiRole", "achievementToastHeading")
        text_layout.addWidget(self.heading_label)
        self.message_label = QLabel()
        self.message_label.setWordWrap(True)
        self.message_label.setProperty("tanukiRole", "achievementToastMessage")
        text_layout.addWidget(self.message_label)
        layout.addLayout(text_layout, stretch=1)
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(frame)
        self.setFixedWidth(360)

    def show_notification(self, snapshot, anchor_rect=None, duration_ms=5000):
        if not isinstance(snapshot, AchievementUnlockNotificationSnapshot):
            return False
        pixmap = _trim_transparent_bounds(
            QPixmap(
                os.path.normpath(
                    str(
                        self.resource_resolver(
                            snapshot.primary_image_relative_path
                        )
                    )
                )
            )
        )
        self.icon_label.setPixmap(
            pixmap.scaled(
                54,
                54,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.heading_label.setText(snapshot.heading)
        self.message_label.setText(snapshot.message)
        self.adjustSize()
        if anchor_rect is not None:
            self.move(
                int(anchor_rect.right() - self.width()),
                int(anchor_rect.top() + 18),
            )
        self.show()
        self.raise_()
        self.hide_timer.start(max(1000, int(duration_ms)))
        return True


def _trim_transparent_bounds(pixmap):
    if pixmap.isNull():
        return QPixmap(1, 1)
    mask = pixmap.mask()
    bounds = QRegion(mask).boundingRect()
    if bounds.isEmpty():
        return pixmap
    return pixmap.copy(bounds)


def _locked_silhouette(pixmap):
    if pixmap.isNull():
        return pixmap
    padding = 4
    dark = _colorize_alpha(pixmap, QColor(18, 18, 24, 218))
    outline = _colorize_alpha(pixmap, QColor(250, 249, 245, 235))
    result = QPixmap(
        pixmap.width() + padding * 2,
        pixmap.height() + padding * 2,
    )
    result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result)
    for offset_x, offset_y in (
        (-2, -2), (0, -2), (2, -2),
        (-2, 0), (2, 0),
        (-2, 2), (0, 2), (2, 2),
    ):
        painter.drawPixmap(
            padding + offset_x,
            padding + offset_y,
            outline,
        )
    painter.drawPixmap(padding, padding, dark)
    painter.end()
    return result


def _colorize_alpha(pixmap, color):
    result = pixmap.copy()
    painter = QPainter(result)
    painter.setCompositionMode(
        QPainter.CompositionMode.CompositionMode_SourceIn
    )
    painter.fillRect(result.rect(), color)
    painter.end()
    return result
