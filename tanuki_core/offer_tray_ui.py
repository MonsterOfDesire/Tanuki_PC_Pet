import os

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from .asset_manager import AssetManager
from .offer_interaction_rules import get_offer_item_definitions


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
        self.setStyleSheet("QFrame { background: transparent; border: none; } QLabel { color: #111; }")
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
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
                        64,
                        64,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                layout.addWidget(icon_label)
        if not has_icon:
            title = QLabel(item_definition.label)
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            title.setStyleSheet("font-weight: bold; font-size: 14px;")
            layout.setContentsMargins(12, 10, 12, 10)
            layout.addWidget(title)
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
    def __init__(self, drop_handler=None, hover_handler=None, clear_hover_handler=None):
        super().__init__(None, Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.setWindowTitle("飲食托盤")
        self.resize(260, 150)
        self.user_position_locked = False
        self._moving_programmatically = False
        layout = QVBoxLayout()
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        badge_row = QHBoxLayout()
        badge_row.setSpacing(16)
        for item_definition in get_offer_item_definitions():
            badge_row.addWidget(
                OfferItemBadge(
                    item_definition,
                    drop_handler=drop_handler,
                    hover_handler=hover_handler,
                    clear_hover_handler=clear_hover_handler,
                )
            )
        layout.addLayout(badge_row)
        layout.addStretch(1)
        self.setLayout(layout)

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
