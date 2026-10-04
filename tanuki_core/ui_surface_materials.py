"""Cached procedural chalk; other skin surfaces retain ordinary QFrame painting."""

import random

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import QFrame


class SkinContentSurface(QFrame):
    def __init__(self, parent=None, *, corner_radius=16):
        super().__init__(parent)
        self.corner_radius = corner_radius
        self._chalk_texture = None
        self._chalk_cache_key = None

    def _build_chalk_texture(self):
        ratio = self.devicePixelRatioF()
        texture = QPixmap(max(1, round(self.width() * ratio)), max(1, round(self.height() * ratio)))
        texture.setDevicePixelRatio(ratio)
        texture.fill(Qt.GlobalColor.transparent)
        painter = QPainter(texture)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rng = random.Random(8107)
        for _ in range(52):
            x, y = rng.uniform(0, self.width()), rng.uniform(0, self.height())
            path = QPainterPath(QPointF(x, y))
            path.cubicTo(x + 45, y - 8, x + 95, y + 7, x + rng.uniform(110, 240), y + rng.uniform(-8, 8))
            painter.setPen(QPen(QColor(199, 213, 181, rng.randrange(2, 6)), rng.uniform(9, 23), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawPath(path)
        for _ in range(min(60000, self.width() * self.height() // 19)):
            color = QColor(203, 215, 183, rng.randrange(5, 18)) if rng.randrange(2) else QColor(6, 23, 16, rng.randrange(8, 25))
            painter.setPen(QPen(color, 0.8))
            painter.drawPoint(QPointF(rng.uniform(0, self.width()), rng.uniform(0, self.height())))
        painter.end()
        return texture

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.property("surfaceRole") != "chalkboard":
            self._chalk_texture = None
            self._chalk_cache_key = None
            return
        key = (self.width(), self.height(), self.devicePixelRatioF())
        if key != self._chalk_cache_key:
            self._chalk_texture = self._build_chalk_texture()
            self._chalk_cache_key = key
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(self.rect()).adjusted(2, 2, -2, -2), self.corner_radius - 2, self.corner_radius - 2)
        painter.setClipPath(clip)
        painter.drawPixmap(0, 0, self._chalk_texture)
