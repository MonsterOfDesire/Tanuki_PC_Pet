"""In-page hover descriptions, independent of native tooltip window policy."""

from weakref import WeakSet

from PyQt6 import sip
from PyQt6.QtCore import QEvent, QObject, QPoint, QTimer, Qt
from PyQt6.QtWidgets import QLabel, QWidget

from .ui_typography import ui_font_pixels


class SettingsHoverHelp(QObject):
    HOVER_DELAY_MS = 350

    def __init__(self, panel):
        super().__init__(panel)
        self.panel = panel
        self._target = None
        self._installed = WeakSet()
        self.label = QLabel(panel)
        self.label.setObjectName("tanukiSettingsHoverHelp")
        self.label.setWordWrap(True)
        self.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.label.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.label.hide()
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(self.HOVER_DELAY_MS)
        self.timer.timeout.connect(self.show_help)
        self.refresh_style()
        self.refresh_targets()

    def refresh_style(self):
        self.label.setStyleSheet(
            "QLabel#tanukiSettingsHoverHelp {"
            "color: #3d2b1e; background: #fff9e7;"
            "border: 1px solid #ac874c; border-radius: 8px;"
            f"padding: 8px 10px; font-size: {ui_font_pixels(13)}px;"
            "}"
        )

    def refresh_targets(self):
        for widget in (self.panel, *self.panel.findChildren(QWidget)):
            if widget is self.label or widget in self._installed:
                continue
            widget.installEventFilter(self)
            self._installed.add(widget)

    def _description_target(self, widget):
        while widget is not None and widget is not self.panel:
            if widget.toolTip():
                return widget
            widget = widget.parentWidget()
        return None

    def hide_help(self):
        self.timer.stop()
        self._target = None
        self.label.hide()

    def show_help(self):
        target = self._target
        if target is None or sip.isdeleted(target) or not self.panel.isVisible() or not target.isVisible():
            self.hide_help()
            return
        text = target.toolTip()
        if not text:
            self.hide_help()
            return
        self.label.setText(text)
        width = min(ui_font_pixels(440), max(1, self.panel.width() - 16))
        self.label.setFixedWidth(width)
        height = max(1, self.label.heightForWidth(width))
        self.label.setFixedHeight(height)
        anchor = target.mapTo(self.panel, QPoint(0, target.height()))
        x = max(8, min(anchor.x(), self.panel.width() - width - 8))
        y = anchor.y() + 8
        if y + height > self.panel.height() - 8:
            y = target.mapTo(self.panel, QPoint()).y() - height - 8
        y = max(8, min(y, self.panel.height() - height - 8))
        self.label.move(x, y)
        self.label.show()
        self.label.raise_()

    def eventFilter(self, watched, event):
        kind = event.type()
        if kind in (QEvent.Type.Enter, QEvent.Type.HoverEnter):
            target = self._description_target(watched)
            if target is not self._target:
                self.hide_help()
                self._target = target
                if target is not None:
                    self.timer.start()
        elif kind == QEvent.Type.ToolTip:
            self._target = self._description_target(watched)
            self.timer.stop()
            self.show_help()
            return True  # Do not also create a native tooltip window.
        elif kind == QEvent.Type.Leave:
            if watched is self._target:
                self.hide_help()
        elif kind in (QEvent.Type.MouseButtonPress, QEvent.Type.Wheel):
            self.hide_help()
        elif watched is self.panel and kind in (
            QEvent.Type.Hide, QEvent.Type.WindowDeactivate,
        ):
            self.hide_help()
        return False
