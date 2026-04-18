import os

from PyQt6.QtCore import QObject, QPoint, QVariantAnimation, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QWidget
from pynput import mouse

from .dashboard_shell_lifecycle import shutdown_listener
from .dashboard_shell_rules import should_request_slide_out

SAFE_WINDOW_MODE = os.environ.get("TANUKI_SAFE_WINDOW_MODE", "0") == "1"


def build_overlay_window_flags():
    flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
    if not SAFE_WINDOW_MODE:
        flags |= Qt.WindowType.Tool
    return flags
class GlobalMouseListener(QObject):
    request_slide_out = pyqtSignal()

    def __init__(self, dashboard, listener_factory=None):
        super().__init__()
        self.dashboard = dashboard
        self._listener_factory = listener_factory or (lambda on_click: mouse.Listener(on_click=on_click))
        self.listener = None
        self._shutdown = False
        self.request_slide_out.connect(self.dashboard.slide_out, Qt.ConnectionType.QueuedConnection)
        self.dashboard.destroyed.connect(lambda *_: self.shutdown())
        self.start()

    def start(self):
        if self._shutdown or self.listener is not None:
            return
        self.listener = self._listener_factory(self.on_click)
        self.listener.start()

    def shutdown(self):
        if self._shutdown:
            return
        self._shutdown = True
        listener = self.listener
        self.listener = None
        shutdown_listener(listener)

    def on_click(self, x, y, button, pressed):
        if self._shutdown:
            return
        if not pressed:
            return
        ratio = self.dashboard.devicePixelRatio()
        logic_point = QPoint(int(x / ratio), int(y / ratio))
        contains_dashboard = self.dashboard.geometry().contains(logic_point)
        if should_request_slide_out(
            is_expanded=self.dashboard.is_expanded,
            contains_dashboard=contains_dashboard,
        ):
            self.request_slide_out.emit()


class SensorZone(QWidget):
    def __init__(self, dashboard):
        super().__init__()
        self.dashboard = dashboard
        self._shutdown = False
        self.setWindowFlags(build_overlay_window_flags())
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.progress = 0.0
        self.glow_anim = QVariantAnimation(self)
        self.glow_anim.setDuration(2000)
        self.glow_anim.setStartValue(0.0)
        self.glow_anim.setEndValue(1.0)
        self.glow_anim.valueChanged.connect(self.update_progress)
        self.glow_anim.finished.connect(self.on_finished)
        self.dashboard.destroyed.connect(lambda *_: self.shutdown())

    def update_progress(self, value):
        self.progress = value
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setBrush(QColor(40, 40, 40, 80))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(self.rect())
        if self.progress > 0:
            fill_h = int(self.height() * self.progress)
            painter.setBrush(QColor(100, 255, 100, 200))
            painter.drawRect(0, self.height() - fill_h, self.width(), fill_h)

    def on_finished(self):
        if self.progress >= 0.99:
            self.dashboard.slide_in([], self)
        self.progress = 0.0
        self.update()

    def enterEvent(self, event):
        if not self._shutdown and not self.dashboard.is_expanded:
            self.glow_anim.start()

    def leaveEvent(self, event):
        self.glow_anim.stop()
        self.progress = 0.0
        self.update()

    def shutdown(self):
        if self._shutdown:
            return
        self._shutdown = True
        self.glow_anim.stop()
        self.progress = 0.0
        self.hide()
        self.close()
