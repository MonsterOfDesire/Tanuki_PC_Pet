import os

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel

from .asset_manager import AssetManager
from .overlay_window import apply_platform_tool_window_attributes


class GroundOfferItemWidget(QLabel):
    DRAG_THRESHOLD = 6

    def __init__(
        self,
        item_kind="",
        icon_relative_path="",
        label="",
        draggable=False,
        drop_handler=None,
        hover_handler=None,
        clear_hover_handler=None,
    ):
        super().__init__(
            None,
            Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint,
        )
        apply_platform_tool_window_attributes(self)
        self.item_kind = item_kind
        self.draggable = bool(draggable)
        self.drop_handler = drop_handler
        self.hover_handler = hover_handler
        self.clear_hover_handler = clear_hover_handler
        self.drag_origin = QPoint()
        self.drag_started = False
        self.drag_offset = QPoint()
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, not self.draggable)
        self.setStyleSheet("background: transparent; border: none;")
        if self.draggable:
            self.setCursor(Qt.CursorShape.OpenHandCursor)

        icon_path = AssetManager.get_resource_path(icon_relative_path) if icon_relative_path else ""
        pixmap = QPixmap()
        if icon_path and os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
        if not pixmap.isNull():
            pixmap = pixmap.scaled(
                48,
                48,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.setPixmap(pixmap)
            self.resize(pixmap.size())
            return

        self.setText(label)
        self.setStyleSheet(
            "background: rgba(255,255,255,225); color: #222; border: 1px solid rgba(0,0,0,90); border-radius: 8px; padding: 4px 6px;"
        )
        self.adjustSize()

    def move_to(self, x, y):
        self.move(int(round(x)), int(round(y)))

    def mousePressEvent(self, event):
        if not self.draggable or event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)
        self.drag_origin = event.globalPosition().toPoint()
        self.drag_offset = event.position().toPoint()
        self.drag_started = False
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        self.raise_()
        self.grabMouse()

    def mouseMoveEvent(self, event):
        if not self.draggable or not (event.buttons() & Qt.MouseButton.LeftButton):
            return super().mouseMoveEvent(event)
        current_pos = event.globalPosition().toPoint()
        if not self.drag_started and (current_pos - self.drag_origin).manhattanLength() >= self.DRAG_THRESHOLD:
            self.drag_started = True
        if not self.drag_started:
            return
        self.move_to(
            current_pos.x() - self.drag_offset.x(),
            current_pos.y() - self.drag_offset.y(),
        )
        if callable(self.hover_handler):
            self.hover_handler(self.item_kind, current_pos)

    def mouseReleaseEvent(self, event):
        if not self.draggable or event.button() != Qt.MouseButton.LeftButton:
            return super().mouseReleaseEvent(event)
        current_pos = event.globalPosition().toPoint()
        self.releaseMouse()
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        if self.drag_started and callable(self.drop_handler):
            self.drop_handler(self, self.item_kind, current_pos)
        elif callable(self.clear_hover_handler):
            self.clear_hover_handler()
        self.drag_started = False
