from PyQt6.QtCore import QEvent, QObject, QPoint, QRect, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QToolButton, QWidget


CHROME_PIN = "pin"
CHROME_MINIMIZE = "minimize"
CHROME_CLOSE = "close"


def _create_chrome_icon(action, color, size=16):
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(QColor(color), 1.8)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    if action == CHROME_PIN:
        path = QPainterPath()
        path.moveTo(5, 2)
        path.lineTo(11, 2)
        path.lineTo(10, 7)
        path.lineTo(13, 9)
        path.lineTo(9, 9)
        path.lineTo(9, 14)
        path.lineTo(8, 16)
        path.lineTo(7, 14)
        path.lineTo(7, 9)
        path.lineTo(3, 9)
        path.lineTo(6, 7)
        path.closeSubpath()
        painter.fillPath(path, QColor(color))
    elif action == CHROME_MINIMIZE:
        painter.drawLine(3, 11, 13, 11)
    else:
        painter.drawLine(4, 4, 12, 12)
        painter.drawLine(12, 4, 4, 12)
    painter.end()
    return QIcon(pixmap)


class WindowChromeControls(QFrame):
    def __init__(self, target_window, variant="dark", parent=None):
        super().__init__(parent or target_window)
        self.target_window = target_window
        self.variant = str(variant or "dark")
        self.setObjectName("tanukiWindowChromeControls")
        self.setProperty("chromeVariant", self.variant)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(3)
        icon_color = "#2f2924" if self.variant == "light" else "#fffaf2"

        self.pin_button = self._create_button(
            CHROME_PIN,
            "視窗置頂",
            icon_color,
            checkable=True,
        )
        self.minimize_button = self._create_button(
            CHROME_MINIMIZE,
            "最小化",
            icon_color,
        )
        self.close_button = self._create_button(
            CHROME_CLOSE,
            "關閉",
            icon_color,
        )
        layout.addWidget(self.pin_button)
        layout.addWidget(self.minimize_button)
        layout.addWidget(self.close_button)
        self.pin_button.toggled.connect(self._set_pinned)
        self.minimize_button.clicked.connect(target_window.showMinimized)
        self.close_button.clicked.connect(target_window.close)
        self.adjustSize()

    def _create_button(self, action, tooltip, icon_color, checkable=False):
        button = QToolButton(self)
        button.setFixedSize(28, 28)
        button.setCheckable(checkable)
        button.setIcon(_create_chrome_icon(action, icon_color))
        button.setIconSize(QPixmap(16, 16).size())
        button.setToolTip(tooltip)
        button.setAccessibleName(tooltip)
        button.setProperty("tanukiRole", "chromeButton")
        button.setProperty("chromeAction", action)
        button.setProperty("chromeVariant", self.variant)
        return button

    def _set_pinned(self, pinned):
        window = self.target_window
        was_visible = window.isVisible()
        geometry = window.geometry()
        position_locked = getattr(window, "user_position_locked", None)
        window.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, bool(pinned))
        window.setGeometry(geometry)
        if position_locked is not None:
            window.user_position_locked = position_locked
        if was_visible:
            window.show()
            window.raise_()


class _WindowDragFilter(QObject):
    def __init__(self, target_window):
        super().__init__(target_window)
        self.target_window = target_window
        self._manual_drag_active = False
        self._drag_offset = QPoint()

    def add_widget(self, widget):
        widget.installEventFilter(self)
        widget.setCursor(Qt.CursorShape.OpenHandCursor)

    def eventFilter(self, watched, event):
        event_type = event.type()
        if event_type == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.target_window.frameGeometry().topLeft()
            handle = self.target_window.windowHandle()
            if handle is not None and handle.startSystemMove():
                self._manual_drag_active = False
            else:
                self._manual_drag_active = True
            watched.setCursor(Qt.CursorShape.ClosedHandCursor)
            return True
        if (
            event_type == QEvent.Type.MouseMove
            and self._manual_drag_active
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
            self.target_window.move(event.globalPosition().toPoint() - self._drag_offset)
            return True
        if event_type == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
            self._manual_drag_active = False
            watched.setCursor(Qt.CursorShape.OpenHandCursor)
            return True
        return super().eventFilter(watched, event)


class _ResizeHandle(QWidget):
    CURSORS = {
        Qt.Edge.LeftEdge: Qt.CursorShape.SizeHorCursor,
        Qt.Edge.RightEdge: Qt.CursorShape.SizeHorCursor,
        Qt.Edge.TopEdge: Qt.CursorShape.SizeVerCursor,
        Qt.Edge.BottomEdge: Qt.CursorShape.SizeVerCursor,
        Qt.Edge.LeftEdge | Qt.Edge.TopEdge: Qt.CursorShape.SizeFDiagCursor,
        Qt.Edge.RightEdge | Qt.Edge.BottomEdge: Qt.CursorShape.SizeFDiagCursor,
        Qt.Edge.RightEdge | Qt.Edge.TopEdge: Qt.CursorShape.SizeBDiagCursor,
        Qt.Edge.LeftEdge | Qt.Edge.BottomEdge: Qt.CursorShape.SizeBDiagCursor,
    }

    def __init__(self, target_window, edges, parent=None):
        super().__init__(parent or target_window)
        self.target_window = target_window
        self.edges = edges
        self.setCursor(self.CURSORS[edges])
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.target_window.windowHandle()
            if handle is not None:
                handle.startSystemResize(self.edges)
            event.accept()
            return
        super().mousePressEvent(event)


class SkinnedToolWindowChrome(QObject):
    HANDLE_WIDTH = 8

    def __init__(self, target_window, drag_widgets=(), controls_variant="dark"):
        super().__init__(target_window)
        self.target_window = target_window
        target_window.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.drag_filter = _WindowDragFilter(target_window)
        for widget in drag_widgets:
            self.add_drag_widget(widget)
        self.controls = WindowChromeControls(
            target_window,
            variant=controls_variant,
            parent=target_window,
        )
        self.resize_handles = {
            edges: _ResizeHandle(target_window, edges, parent=target_window)
            for edges in (
                Qt.Edge.LeftEdge,
                Qt.Edge.RightEdge,
                Qt.Edge.TopEdge,
                Qt.Edge.BottomEdge,
                Qt.Edge.LeftEdge | Qt.Edge.TopEdge,
                Qt.Edge.RightEdge | Qt.Edge.TopEdge,
                Qt.Edge.LeftEdge | Qt.Edge.BottomEdge,
                Qt.Edge.RightEdge | Qt.Edge.BottomEdge,
            )
        }

    def add_drag_widget(self, widget):
        self.drag_filter.add_widget(widget)

    def refresh_geometry(self):
        width = self.target_window.width()
        height = self.target_window.height()
        edge = self.HANDLE_WIDTH
        corner = edge * 2
        geometries = {
            Qt.Edge.LeftEdge: QRect(0, corner, edge, max(0, height - corner * 2)),
            Qt.Edge.RightEdge: QRect(width - edge, corner, edge, max(0, height - corner * 2)),
            Qt.Edge.TopEdge: QRect(corner, 0, max(0, width - corner * 2), edge),
            Qt.Edge.BottomEdge: QRect(corner, height - edge, max(0, width - corner * 2), edge),
            Qt.Edge.LeftEdge | Qt.Edge.TopEdge: QRect(0, 0, corner, corner),
            Qt.Edge.RightEdge | Qt.Edge.TopEdge: QRect(width - corner, 0, corner, corner),
            Qt.Edge.LeftEdge | Qt.Edge.BottomEdge: QRect(0, height - corner, corner, corner),
            Qt.Edge.RightEdge | Qt.Edge.BottomEdge: QRect(
                width - corner,
                height - corner,
                corner,
                corner,
            ),
        }
        for edges, handle in self.resize_handles.items():
            handle.setGeometry(geometries[edges])
            handle.raise_()
        self.controls.raise_()
