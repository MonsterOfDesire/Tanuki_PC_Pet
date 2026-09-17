from __future__ import annotations

from PyQt6.QtCore import (
    QObject,
    QPoint,
    QPointF,
    QRect,
    QRectF,
    QSize,
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import QColor, QCursor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QApplication, QWidget

from .achievement_memory_capture import capture_virtual_desktop_rect_image


MANUAL_CAMERA_DEFAULT_ASPECT = "16:9"
MANUAL_CAMERA_OUTPUT_SIZES = {
    "4:3": QSize(400, 300),
    "16:9": QSize(534, 300),
}
MANUAL_CAMERA_CAPTURE_SETTLE_MS = 80
MANUAL_CAMERA_POINTER_INTERVAL_MS = 16
MANUAL_CAMERA_POINTER_FOLLOW_FACTOR = 0.65
MANUAL_CAMERA_TITLE_HEIGHT = 30
MANUAL_CAMERA_TITLE_GAP = 6
MANUAL_CAMERA_INPUT_ALPHA = 1


def normalize_manual_camera_aspect(value):
    value = str(value or MANUAL_CAMERA_DEFAULT_ASPECT)
    return value if value in MANUAL_CAMERA_OUTPUT_SIZES else MANUAL_CAMERA_DEFAULT_ASPECT


def fit_viewfinder_size(output_size, available_size, *, margin=24):
    output_size = QSize(output_size)
    available_size = QSize(available_size)
    usable_width = max(1, available_size.width() - int(margin) * 2)
    usable_height = max(1, available_size.height() - int(margin) * 2)
    scale = min(
        1.0,
        usable_width / float(max(1, output_size.width())),
        usable_height / float(max(1, output_size.height())),
    )
    return QSize(
        max(1, int(round(output_size.width() * scale))),
        max(1, int(round(output_size.height() * scale))),
    )


def virtual_desktop_geometry(screens=None):
    screens = tuple(QApplication.screens() if screens is None else screens)
    if not screens:
        return QRect()
    rect = QRect(screens[0].geometry())
    for screen in screens[1:]:
        rect = rect.united(screen.geometry())
    return rect


def interpolate_pointer_center(current, target, *, factor=MANUAL_CAMERA_POINTER_FOLLOW_FACTOR):
    """Return one high-frequency eased step without quantizing to coarse pixels."""
    current = QPointF(current)
    target = QPointF(target)
    dx = target.x() - current.x()
    dy = target.y() - current.y()
    if abs(dx) < 0.35 and abs(dy) < 0.35:
        return target
    factor = max(0.0, min(1.0, float(factor)))
    return QPointF(
        current.x() + dx * factor,
        current.y() + dy * factor,
    )


class ManualCameraOverlay(QWidget):
    capture_requested = pyqtSignal(QRect, QSize)
    cancelled = pyqtSignal()

    def __init__(self, *, aspect_key=MANUAL_CAMERA_DEFAULT_ASPECT, hint_text="", parent=None):
        flags = (
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        super().__init__(parent, flags)
        self.aspect_key = normalize_manual_camera_aspect(aspect_key)
        self.hint_text = str(hint_text or "")
        self._frame_rect_global = QRect()
        cursor = QCursor.pos()
        self._pointer_center = QPointF(cursor)
        self._pointer_timer = QTimer(self)
        self._pointer_timer.setInterval(MANUAL_CAMERA_POINTER_INTERVAL_MS)
        self._pointer_timer.timeout.connect(self._follow_pointer)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        geometry = virtual_desktop_geometry()
        if not geometry.isEmpty():
            self.setGeometry(geometry)
        self.move_viewfinder(cursor, immediate=True)

    @property
    def output_size(self):
        return QSize(MANUAL_CAMERA_OUTPUT_SIZES[self.aspect_key])

    @property
    def frame_rect_global(self):
        return QRect(self._frame_rect_global)

    def show_camera(self):
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
        self.grabKeyboard()
        self._pointer_timer.start()

    def toggle_aspect(self):
        self.aspect_key = "4:3" if self.aspect_key == "16:9" else "16:9"
        self.move_viewfinder(QCursor.pos(), immediate=True)

    def move_viewfinder(self, global_pos, *, immediate=False):
        point = QPoint(global_pos)
        if immediate:
            self._pointer_center = QPointF(point)
        else:
            self._pointer_center = interpolate_pointer_center(
                self._pointer_center,
                QPointF(point),
            )
        return self._position_viewfinder(point)

    def _follow_pointer(self):
        self.move_viewfinder(QCursor.pos())

    def _position_viewfinder(self, target_point):
        point = QPoint(
            int(round(self._pointer_center.x())),
            int(round(self._pointer_center.y())),
        )
        target_point = QPoint(target_point)
        screen = QApplication.screenAt(target_point)
        if screen is None:
            screens = QApplication.screens()
            screen = screens[0] if screens else None
        if screen is None:
            return QRect()
        bounds = screen.availableGeometry()
        size = fit_viewfinder_size(self.output_size, bounds.size())
        left = max(bounds.left(), min(point.x() - size.width() // 2, bounds.right() - size.width() + 1))
        title_clearance = (
            MANUAL_CAMERA_TITLE_HEIGHT + MANUAL_CAMERA_TITLE_GAP
            if self.hint_text
            else 0
        )
        preferred_top = point.y() - size.height() // 2
        minimum_top = bounds.top() + title_clearance
        maximum_top = bounds.bottom() - size.height() + 1
        if minimum_top > maximum_top:
            minimum_top = bounds.top()
        top = max(minimum_top, min(preferred_top, maximum_top))
        self._frame_rect_global = QRect(QPoint(left, top), size)
        self.update()
        return QRect(self._frame_rect_global)

    def _frame_rect_local(self):
        rect = QRect(self._frame_rect_global)
        rect.translate(-self.geometry().x(), -self.geometry().y())
        return rect

    def mouseMoveEvent(self, event):
        # The 16 ms cursor sampler drives the frame. Keeping this handler free
        # of direct geometry changes prevents coarse native mouse events from
        # making the viewfinder visibly jump.
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Capture on press instead of waiting for a click/release pair.
            # This keeps transparent layered-window focus changes from making
            # the shutter feel unresponsive on Windows.
            self.capture_requested.emit(self.frame_rect_global, self.output_size)
            event.accept()
            return
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.cancelled.emit()
            event.accept()
            return
        if key in (Qt.Key.Key_Tab, Qt.Key.Key_Space):
            self.toggle_aspect()
            event.accept()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        self._pointer_timer.stop()
        try:
            self.releaseKeyboard()
        except Exception:
            pass
        super().closeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), QColor(52, 52, 52, 178))
        frame = QRectF(self._frame_rect_local())
        if frame.isEmpty():
            return

        # A fully transparent pixel in a Windows layered window is also
        # transparent to native hit testing. Keep the viewfinder visually
        # clear but give it the smallest non-zero alpha so real desktop clicks
        # reach this overlay instead of the window behind it.
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(frame, QColor(0, 0, 0, MANUAL_CAMERA_INPUT_ALPHA))
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        painter.setPen(QPen(QColor(255, 250, 232, 150), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(frame)
        grid_pen = QPen(QColor(255, 255, 255, 48), 1.0, Qt.PenStyle.DashLine)
        painter.setPen(grid_pen)
        for ratio in (1.0 / 3.0, 2.0 / 3.0):
            x = frame.left() + frame.width() * ratio
            y = frame.top() + frame.height() * ratio
            painter.drawLine(int(x), int(frame.top()), int(x), int(frame.bottom()))
            painter.drawLine(int(frame.left()), int(y), int(frame.right()), int(y))

        corner_pen = QPen(QColor("#f2bf5d"), 5.0)
        corner_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(corner_pen)
        length = min(86.0, frame.width() * 0.08, frame.height() * 0.12)
        corners = (
            (frame.left(), frame.top(), 1, 1),
            (frame.right(), frame.top(), -1, 1),
            (frame.left(), frame.bottom(), 1, -1),
            (frame.right(), frame.bottom(), -1, -1),
        )
        for x, y, dx, dy in corners:
            painter.drawLine(int(x), int(y), int(x + dx * length), int(y))
            painter.drawLine(int(x), int(y), int(x), int(y + dy * length))

        if self.hint_text:
            title_rect = QRectF(
                frame.left(),
                frame.top() - MANUAL_CAMERA_TITLE_HEIGHT - MANUAL_CAMERA_TITLE_GAP,
                frame.width(),
                MANUAL_CAMERA_TITLE_HEIGHT,
            )
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(28, 28, 28, 205))
            painter.drawRoundedRect(title_rect, 5.0, 5.0)
            painter.setPen(QColor(255, 255, 255, 215))
            painter.drawText(
                title_rect.adjusted(10.0, 0.0, -10.0, 0.0),
                Qt.AlignmentFlag.AlignCenter,
                self.hint_text,
            )


class ManualCameraController(QObject):
    active_changed = pyqtSignal(bool)
    capture_finished = pyqtSignal(object)
    status_changed = pyqtSignal(str)

    def __init__(
        self,
        *,
        album_service,
        capacity_provider,
        time_scale_provider,
        hint_provider=None,
        image_provider=None,
        overlay_factory=None,
        parent=None,
    ):
        super().__init__(parent)
        self.album_service = album_service
        self.capacity_provider = capacity_provider
        self.time_scale_provider = time_scale_provider
        self.hint_provider = hint_provider or (lambda: "")
        self.image_provider = image_provider or capture_virtual_desktop_rect_image
        self.overlay_factory = overlay_factory or self._build_overlay
        self.overlay = None
        self.last_aspect_key = MANUAL_CAMERA_DEFAULT_ASPECT
        self._capture_pending = False

    @property
    def active(self):
        return self.overlay is not None

    def availability_reason(self):
        if self.active:
            return ""
        if abs(float(self.time_scale_provider()) - 1.0) > 1e-6:
            return "speed"
        snapshot = self.album_service.snapshot(
            mode="events",
            capacity=int(self.capacity_provider()),
        )
        if snapshot.full:
            return "full"
        return ""

    def toggle(self):
        if self.active:
            self.cancel()
            return True
        return self.start()

    def start(self):
        reason = self.availability_reason()
        if reason:
            self.status_changed.emit(reason)
            return False
        overlay = self.overlay_factory(
            self.last_aspect_key,
            str(self.hint_provider() or ""),
        )
        self.overlay = overlay
        overlay.capture_requested.connect(self._request_capture)
        overlay.cancelled.connect(self.cancel)
        overlay.destroyed.connect(self._overlay_destroyed)
        overlay.show_camera()
        self.active_changed.emit(True)
        return True

    def cancel(self):
        overlay = self.overlay
        self.overlay = None
        self._capture_pending = False
        if overlay is not None:
            self.last_aspect_key = normalize_manual_camera_aspect(
                getattr(overlay, "aspect_key", self.last_aspect_key)
            )
            overlay.close()
            overlay.deleteLater()
            self.active_changed.emit(False)
        return overlay is not None

    def _request_capture(self, rect, output_size):
        if self._capture_pending or self.overlay is None:
            return
        if abs(float(self.time_scale_provider()) - 1.0) > 1e-6:
            self.status_changed.emit("speed")
            self.cancel()
            return
        self._capture_pending = True
        self.overlay.hide()
        QTimer.singleShot(
            MANUAL_CAMERA_CAPTURE_SETTLE_MS,
            lambda: self._complete_capture(QRect(rect), QSize(output_size)),
        )

    def _complete_capture(self, rect, output_size):
        if not self._capture_pending:
            return
        self._capture_pending = False
        image = self.image_provider(rect, output_size)
        path = self.album_service.capture_manual(
            image,
            capacity=int(self.capacity_provider()),
            kind="manual",
        )
        self.cancel()
        self.capture_finished.emit(path)
        self.status_changed.emit("saved" if path is not None else "failed")

    def _overlay_destroyed(self, *_args):
        if self.overlay is not None:
            self.overlay = None
            self._capture_pending = False
            self.active_changed.emit(False)

    @staticmethod
    def _build_overlay(aspect_key, hint_text):
        return ManualCameraOverlay(
            aspect_key=aspect_key,
            hint_text=hint_text,
        )
