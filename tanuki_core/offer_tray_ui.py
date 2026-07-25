import os

from PyQt6.QtCore import QPoint, QTimer, Qt
from PyQt6.QtGui import QGuiApplication, QPixmap
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from .asset_manager import AssetManager
from .offer_interaction_rules import get_offer_item_definitions
from .skinned_window_frame import SkinnedWindowFrame
from .ui_skin_assets import UiSkinAssets
from .ui_skin_spec import SKIN_DIET
from .ui_theme import DEFAULT_UI_THEME, build_ui_stylesheet
from .window_chrome import SkinnedToolWindowChrome


class OfferDragGhost(QFrame):
    def __init__(self, label, accent_color, icon_relative_path=""):
        super().__init__(None, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        icon_path = AssetManager.get_resource_path(icon_relative_path) if icon_relative_path else ""
        has_icon = False
        if icon_path and os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                has_icon = True
                icon_label = QLabel()
                icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                icon_label.setPixmap(
                    pixmap.scaled(
                        56,
                        56,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                layout.addWidget(icon_label)
        if not has_icon:
            self.label = QLabel(label)
            self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.label.setStyleSheet("color: #111; font-weight: bold;")
            layout.setContentsMargins(10, 8, 10, 8)
            layout.addWidget(self.label)
            self.setStyleSheet(
                f"QFrame {{ background: {accent_color}; border: 2px solid rgba(20,20,20,180); border-radius: 10px; }}"
            )
        else:
            self.setStyleSheet("QFrame { background: transparent; border: none; }")
        self.setLayout(layout)
        self.adjustSize()

    def move_to_cursor(self, global_pos):
        self.move(global_pos.x() - (self.width() // 2), global_pos.y() - (self.height() // 2))


class OfferItemBadge(QFrame):
    DRAG_THRESHOLD = 10

    def __init__(self, item_definition, drop_handler=None, hover_handler=None, clear_hover_handler=None):
        super().__init__()
        self.item_definition = item_definition
        self.drop_handler = drop_handler
        self.hover_handler = hover_handler
        self.clear_hover_handler = clear_hover_handler
        self.drag_origin = QPoint()
        self.drag_started = False
        self.drag_ghost = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setProperty("tanukiRole", "offerItemBadge")
        self.setAccessibleName(item_definition.label)
        self.setToolTip(f"拖曳{item_definition.label}給角色")
        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        icon_path = AssetManager.get_resource_path(item_definition.icon_relative_path) if item_definition.icon_relative_path else ""
        has_icon = False
        if icon_path and os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                has_icon = True
                icon_label = QLabel()
                icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                icon_label.setPixmap(
                    pixmap.scaled(
                        56,
                        56,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                layout.addWidget(icon_label)
        self.title_label = QLabel(item_definition.label)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setProperty("tanukiRole", "offerItemName")
        if not has_icon:
            layout.setContentsMargins(10, 8, 10, 8)
        layout.addWidget(self.title_label)
        self.setLayout(layout)

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)
        self.drag_origin = event.globalPosition().toPoint()
        self.drag_started = False
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        self.grabMouse()

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return super().mouseMoveEvent(event)
        current_pos = event.globalPosition().toPoint()
        if not self.drag_started and (current_pos - self.drag_origin).manhattanLength() >= self.DRAG_THRESHOLD:
            self.drag_started = True
            self.drag_ghost = OfferDragGhost(
                self.item_definition.label,
                self.item_definition.accent_color,
                self.item_definition.icon_relative_path,
            )
            self.drag_ghost.show()
        if self.drag_started and self.drag_ghost is not None:
            self.drag_ghost.move_to_cursor(current_pos)
            if callable(self.hover_handler):
                self.hover_handler(self.item_definition.kind, current_pos)

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return super().mouseReleaseEvent(event)
        current_pos = event.globalPosition().toPoint()
        if self.drag_ghost is not None:
            self.drag_ghost.close()
            self.drag_ghost.deleteLater()
            self.drag_ghost = None
        self.releaseMouse()
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        if self.drag_started and callable(self.drop_handler):
            self.drop_handler(self.item_definition.kind, current_pos)
        elif callable(self.clear_hover_handler):
            self.clear_hover_handler()
        self.drag_started = False


class OfferTrayWindow(QWidget):
    def __init__(
        self,
        drop_handler=None,
        hover_handler=None,
        clear_hover_handler=None,
        assets=None,
        theme=DEFAULT_UI_THEME,
    ):
        super().__init__(None, Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.setObjectName("tanukiOfferTray")
        self.setWindowTitle("飲食托盤")
        self.resize(760, 570)
        self.user_position_locked = False
        self._moving_programmatically = False
        self._pending_programmatic_move = False
        self.assets = assets or UiSkinAssets(AssetManager.get_resource_path)
        self.theme = theme
        self.item_badges = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.skin_frame = SkinnedWindowFrame(
            self.assets,
            SKIN_DIET,
            parent=self,
            theme=theme,
        )
        self.skin_frame.set_content_margins(
            theme.spacing_sm,
            theme.spacing_sm,
            theme.spacing_sm,
            theme.spacing_sm,
        )

        tray_content = QWidget()
        tray_layout = QVBoxLayout(tray_content)
        tray_layout.setContentsMargins(0, 0, 0, 0)
        tray_layout.setSpacing(theme.spacing_xs)

        badge_row = QHBoxLayout()
        badge_row.setContentsMargins(0, 0, 0, 0)
        badge_row.setSpacing(theme.spacing_sm)
        badge_row.addStretch(1)
        for item_definition in get_offer_item_definitions():
            badge = OfferItemBadge(
                item_definition,
                drop_handler=drop_handler,
                hover_handler=hover_handler,
                clear_hover_handler=clear_hover_handler,
            )
            self.item_badges.append(badge)
            badge_row.addWidget(badge)
        badge_row.addStretch(1)
        tray_layout.addLayout(badge_row)
        tray_layout.addStretch(1)
        instruction_row = QHBoxLayout()
        instruction_row.setContentsMargins(0, 0, 0, 0)
        instruction_row.addStretch(1)
        self.instruction_label = QLabel("拖曳給角色")
        self.instruction_label.setProperty("tanukiRole", "offerInstruction")
        self.instruction_label.setToolTip("按住食物並拖曳到桌面角色身上")
        instruction_row.addWidget(self.instruction_label)
        tray_layout.addLayout(instruction_row)
        self.skin_frame.set_content_widget(tray_content)
        layout.addWidget(self.skin_frame)
        self.setStyleSheet(build_ui_stylesheet(theme))

        self.chrome_drag_zone = QFrame(self)
        self.chrome_drag_zone.setObjectName("tanukiDietChromeDragZone")
        self.chrome_drag_zone.setAccessibleName("拖曳飲食托盤視窗")
        self.window_chrome = SkinnedToolWindowChrome(
            self,
            drag_widgets=(self.chrome_drag_zone,),
            controls_variant="light",
        )
        self._update_chrome_geometry()

    def move_near_anchor(self, x, y):
        anchor = QPoint(int(x), int(y))
        screen = QGuiApplication.screenAt(anchor) or self.screen() or QGuiApplication.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            frame_geometry = self.frameGeometry()
            frame_width = max(self.width(), frame_geometry.width())
            frame_height = max(self.height(), frame_geometry.height())
            max_x = max(available.x(), available.x() + available.width() - frame_width)
            max_y = max(available.y(), available.y() + available.height() - frame_height)
            x = max(available.x(), min(int(x), max_x))
            y = max(available.y(), min(int(y), max_y))
        self._moving_programmatically = True
        self._pending_programmatic_move = True
        try:
            self.move(int(x), int(y))
        finally:
            self._moving_programmatically = False

    def moveEvent(self, event):
        if self._moving_programmatically or self._pending_programmatic_move:
            self._pending_programmatic_move = False
        else:
            self.user_position_locked = True
        super().moveEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "window_chrome"):
            self._update_chrome_geometry()
            QTimer.singleShot(0, self._update_chrome_geometry)

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, "window_chrome"):
            QTimer.singleShot(0, self._update_chrome_geometry)

    def _update_chrome_geometry(self):
        scene = self.skin_frame.scene_geometry()
        if scene.width() <= 0 or scene.height() <= 0:
            scene = self.skin_frame.rect()
        scene_x = self.skin_frame.x() + scene.x()
        scene_y = self.skin_frame.y() + scene.y()
        self.chrome_drag_zone.setGeometry(
            int(round(scene_x + scene.width() * 0.240)),
            int(round(scene_y + scene.height() * 0.025)),
            int(round(scene.width() * 0.500)),
            int(round(scene.height() * 0.145)),
        )
        controls = self.window_chrome.controls
        controls.adjustSize()
        controls.move(
            int(round(scene_x + scene.width() - controls.width() - scene.width() * 0.012)),
            int(round(scene_y + scene.height() * 0.075)),
        )
        self.chrome_drag_zone.raise_()
        self.window_chrome.refresh_geometry()
