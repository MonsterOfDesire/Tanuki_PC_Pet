"""Painted noticeboard controls; all hit targets remain native Qt widgets."""

import math

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QFrame, QGroupBox, QLabel, QPushButton
from .ui_typography import ui_font_pixels, ui_text_scale


INK = "#59351e"
GREEN = "#608c35"


def paint_symbol(painter, rect, name, color=GREEN):
    """Small vector illustrations, independent of emoji/font availability."""
    painter.save()
    painter.translate(rect.x(), rect.y())
    painter.scale(rect.width() / 32, rect.height() / 32)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor(color), 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    if name == "leaf":
        painter.setPen(Qt.PenStyle.NoPen)
        for flipped in (False, True):
            painter.save()
            if flipped:
                painter.translate(28, 7)
                painter.scale(-0.7, 0.7)
            path = QPainterPath(QPointF(15, 29))
            path.cubicTo(2, 24, 0, 12, 3, 6)
            path.cubicTo(14, 7, 21, 16, 15, 29)
            painter.setBrush(QColor(color))
            painter.drawPath(path)
            painter.setPen(QPen(QColor("#edf1c9"), 1.25))
            painter.drawLine(QPointF(14, 28), QPointF(7, 12))
            painter.restore()
        painter.setPen(QPen(QColor(color), 2))
        painter.drawLine(QPointF(16, 30), QPointF(24, 7))
    elif name == "globe":
        painter.drawEllipse(QRectF(4, 4, 24, 24))
        painter.drawEllipse(QRectF(10, 4, 12, 24))
        painter.drawLine(QPointF(4, 16), QPointF(28, 16))
        painter.drawLine(QPointF(7, 9), QPointF(25, 9))
        painter.drawLine(QPointF(7, 23), QPointF(25, 23))
    elif name == "heart":
        path = QPainterPath(QPointF(16, 28))
        path.cubicTo(-5, 13, 6, -1, 16, 10)
        path.cubicTo(27, -1, 38, 13, 16, 28)
        painter.fillPath(path, QColor(color))
    elif name == "clock":
        painter.drawEllipse(QRectF(4, 4, 24, 24))
        painter.drawLine(QPointF(16, 8), QPointF(16, 17))
        painter.drawLine(QPointF(16, 17), QPointF(23, 17))
    elif name == "display":
        painter.drawRoundedRect(QRectF(3, 5, 26, 18), 2, 2)
        painter.drawLine(QPointF(16, 23), QPointF(16, 28))
        painter.drawLine(QPointF(10, 28), QPointF(22, 28))
    elif name == "sleep":
        painter.drawLine(QPointF(3, 8), QPointF(3, 27))
        painter.drawLine(QPointF(29, 15), QPointF(29, 27))
        painter.drawLine(QPointF(3, 24), QPointF(29, 24))
        painter.setBrush(QColor(color))
        painter.drawEllipse(QRectF(7, 10, 6, 6))
        painter.drawRoundedRect(QRectF(15, 12, 13, 9), 2, 2)
    elif name == "sparkles":
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(color))
        for x, y, r in ((12, 13, 11), (25, 25, 6), (26, 5, 4)):
            path = QPainterPath(QPointF(x, y-r))
            path.quadTo(x+2, y-2, x+r, y)
            path.quadTo(x+2, y+2, x, y+r)
            path.quadTo(x-2, y+2, x-r, y)
            path.quadTo(x-2, y-2, x, y-r)
            painter.drawPath(path)
    elif name == "race":
        painter.setBrush(QColor(color))
        painter.drawEllipse(QRectF(19, 2, 6, 6))
        painter.setPen(QPen(QColor(color), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        path = QPainterPath(QPointF(5, 15))
        path.lineTo(11, 10); path.lineTo(19, 12); path.lineTo(25, 19); path.lineTo(29, 17)
        painter.drawPath(path)
        path = QPainterPath(QPointF(19, 12))
        path.lineTo(14, 21); path.lineTo(20, 26); path.lineTo(19, 30)
        painter.drawPath(path)
        painter.drawLine(QPointF(14, 21), QPointF(5, 27))
    elif name == "music":
        painter.drawLine(QPointF(11, 24), QPointF(11, 7))
        painter.drawLine(QPointF(27, 20), QPointF(27, 3))
        painter.drawLine(QPointF(11, 7), QPointF(27, 3))
        painter.drawLine(QPointF(11, 12), QPointF(27, 8))
        painter.setBrush(QColor(color))
        painter.drawEllipse(QRectF(3, 21, 8, 6))
        painter.drawEllipse(QRectF(19, 17, 8, 6))
    elif name == "sun":
        painter.setBrush(QColor("#e8ac29"))
        painter.setPen(QPen(QColor("#dfa024"), 2.5))
        painter.drawEllipse(QRectF(9, 9, 14, 14))
        for i in range(8):
            a = i * math.pi / 4
            painter.drawLine(QPointF(16+11*math.cos(a), 16+11*math.sin(a)), QPointF(16+15*math.cos(a), 16+15*math.sin(a)))
    elif name == "camera":
        painter.drawRoundedRect(QRectF(3, 9, 26, 19), 3, 3)
        painter.drawRect(QRectF(9, 5, 11, 4))
        painter.drawEllipse(QRectF(11, 13, 10, 10))
    elif name == "album":
        painter.drawRoundedRect(QRectF(6, 4, 23, 24), 2, 2)
        painter.drawLine(QPointF(2, 9), QPointF(2, 30))
        painter.drawLine(QPointF(2, 30), QPointF(24, 30))
        painter.drawEllipse(QRectF(11, 9, 4, 4))
        path = QPainterPath(QPointF(9, 24)); path.lineTo(16, 16); path.lineTo(20, 20); path.lineTo(25, 15)
        painter.drawPath(path)
    elif name == "refresh":
        painter.drawArc(QRectF(5, 5, 22, 22), 35*16, 265*16)
        painter.drawLine(QPointF(27, 4), QPointF(27, 13))
        painter.drawLine(QPointF(27, 13), QPointF(18, 13))
    elif name == "wrench":
        path = QPainterPath(QPointF(6, 29))
        path.lineTo(18, 17); path.cubicTo(28, 21, 32, 11, 28, 5)
        path.lineTo(23, 11); path.lineTo(19, 8); path.lineTo(24, 2)
        path.cubicTo(14, 0, 10, 8, 14, 14); path.lineTo(2, 25)
        path.quadTo(1, 30, 6, 29)
        painter.fillPath(path, QColor(color))
    else:
        painter.drawEllipse(QRectF(5, 5, 22, 22))
        painter.drawLine(QPointF(16, 10), QPointF(16, 22))
        painter.drawLine(QPointF(10, 16), QPointF(22, 16))
    painter.restore()


class NoticeboardLabel(QLabel):
    def __init__(self, text="", parent=None, symbol="leaf"):
        super().__init__(text, parent)
        self.symbol = symbol
        self.avatar = None
        self.art_scale = 1.0
        self.setMargin(0)
        self.setContentsMargins(28, 0, 0, 0)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.setWordWrap(True)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = min(26*self.art_scale, max(20, self.height()-2))
        rect = QRectF(0, (self.height()-side)/2, side, side)
        if self.avatar is not None and not self.avatar.isNull():
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.drawPixmap(rect, self.avatar, QRectF(self.avatar.rect()))
        else:
            paint_symbol(painter, rect, self.symbol)


class NoticeboardSection(QGroupBox):
    def __init__(self, title="", parent=None):
        super().__init__(title, parent)
        self.embedded = False
        self.heading = None
        self.art_scale = 1.0
        self.setStyleSheet("QGroupBox { border: none; background: transparent; margin: 0; padding: 0; }")

    def paintEvent(self, event):
        if self.embedded:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        scale = self.art_scale
        shade = QLinearGradient(0, 0, 0, self.height())
        shade.setColorAt(0, QColor(255, 255, 248, 112))
        shade.setColorAt(1, QColor(255, 242, 208, 70))
        painter.setBrush(shade)
        painter.setPen(QPen(QColor(210, 175, 111, 105), 1))
        painter.drawRoundedRect(rect, 17, 17)
        paint_symbol(painter, QRectF(12*scale, 10*scale, 27*scale, 27*scale), "leaf")
        font = QFont(self.font()); font.setPixelSize(ui_font_pixels(20*scale)); font.setBold(True)
        painter.setFont(font); painter.setPen(QColor(INK))
        painter.drawText(QRectF(46*scale, 8*scale, self.width()-60*scale, 32*scale*max(1.0, ui_text_scale())), Qt.AlignmentFlag.AlignVCenter, self.heading or self.title())
        painter.setPen(QPen(QColor(190, 149, 86, 150), 1, Qt.PenStyle.DashLine))
        heading_bottom = 40*scale*max(1.0, ui_text_scale())
        painter.drawLine(QPointF(14*scale, heading_bottom), QPointF(self.width()-14*scale, heading_bottom))
        painter.setOpacity(0.24)
        paint_symbol(painter, QRectF(self.width()-30, self.height()-25, 22, 22), "leaf")


class NoticeboardTab(QPushButton):
    def __init__(self, symbol, parent=None):
        super().__init__(parent)
        self.symbol = symbol
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("QPushButton { border: none; background: transparent; padding: 0; }")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        w, h = self.width(), self.height()
        if self.isChecked() or self.underMouse():
            path = QPainterPath(QPointF(5, h-3))
            path.lineTo(11, 15); path.quadTo(13, 5, 26, 5)
            path.lineTo(w-27, 5); path.quadTo(w-14, 5, w-12, 17)
            path.lineTo(w-5, h-3); path.closeSubpath()
            painter.setBrush(QColor("#fbf3df") if self.isChecked() else QColor(243, 213, 149, 55))
            painter.setPen(QPen(QColor("#bb9961"), 1))
            painter.drawPath(path)
        color = INK if self.isChecked() else "#f0d9b2"
        font = QFont(self.font()); font.setPixelSize(ui_font_pixels(max(15, min(30, int(h*0.39)))))
        font.setBold(True)
        while QFontMetrics(font).horizontalAdvance(self.text()) > w-65 and font.pixelSize() > 12:
            font.setPixelSize(font.pixelSize()-1)
        painter.setFont(font)
        text_width = QFontMetrics(font).horizontalAdvance(self.text())
        icon_size = min(36, h*0.51)
        x = (w-text_width-icon_size-12)/2
        paint_symbol(painter, QRectF(x, (h-icon_size)/2+3, icon_size, icon_size), self.symbol, GREEN if self.isChecked() else color)
        painter.setPen(QColor(color))
        painter.drawText(QRectF(x+icon_size+12, 3, text_width+3, h-3), Qt.AlignmentFlag.AlignVCenter, self.text())
        if self.hasFocus():
            painter.setPen(QPen(QColor("#bba05f"), 1, Qt.PenStyle.DotLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(QRectF(8, 6, w-16, h-10), 9, 9)


class NoticeboardOption(QPushButton):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("QPushButton { border: none; background: transparent; min-width: 0; padding: 0; }")
        self.setFixedHeight(30)
        self.art_scale = 1.0

    def sizeHint(self):
        font = QFont(self.font()); font.setPixelSize(ui_font_pixels(max(12, round(14*self.art_scale))))
        font.setBold(True)
        metrics = QFontMetrics(font)
        return QSize(max(30, metrics.horizontalAdvance(self.text())+round(10*self.art_scale)), max(round(30*self.art_scale), metrics.height()+14))

    def minimumSizeHint(self):
        return self.sizeHint()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        selected = self.isChecked()
        if not self.isEnabled():
            painter.setOpacity(0.45)
        if selected:
            color = "#3e6035" if self.isDown() else ("#648e52" if self.underMouse() else "#557f45")
            painter.setBrush(QColor(color)); painter.setPen(QPen(QColor("#779564"), 0.8))
            painter.drawRoundedRect(rect, 14, 14)
        elif self.isDown() and self.isEnabled():
            painter.setBrush(QColor("#d3dfbd")); painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect, 14, 14)
        elif self.underMouse() and self.isEnabled():
            painter.setBrush(QColor(124, 162, 70, 38)); painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect, 14, 14)
        else:
            if self.property("segmentPosition") not in {"last", "single"}:
                painter.setPen(QPen(QColor(191, 154, 100, 120), 1))
                painter.drawLine(QPointF(self.width()-1, 5), QPointF(self.width()-1, self.height()-5))
        font = QFont(self.font()); font.setPixelSize(ui_font_pixels(max(12, round(14*self.art_scale)))); font.setBold(selected)
        painter.setFont(font)
        painter.setPen(QColor("#fffced" if selected else INK))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text())
        if self.hasFocus():
            painter.setPen(QPen(QColor("#aa8447"), 1, Qt.PenStyle.DotLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 8, 8)


class NoticeboardRail(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("QFrame { border: none; background: transparent; }")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(255, 251, 236, 100))
        painter.setPen(QPen(QColor("#d6bc8d"), 1))
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 12, 12)


class NoticeboardAction(QPushButton):
    """Flat paper action retaining its symbol and keyboard focus."""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.symbol = "wrench"
        self.primary = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("QPushButton { border: none; background: transparent; padding: 0; }")
        self.setMinimumHeight(32)

    def sizeHint(self):
        return QSize(self.fontMetrics().horizontalAdvance(self.text())+46, 34)

    def minimumSizeHint(self):
        return self.sizeHint()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        active = self.isEnabled() and (self.primary or self.underMouse() or self.isDown())
        if not self.isEnabled():
            painter.setOpacity(0.45)
        fill = "#3e6035" if self.isDown() else ("#648e52" if self.underMouse() else "#557f45")
        painter.setBrush(QColor(fill if active else "#f7f0dd"))
        painter.setPen(QPen(QColor("#779564" if active else "#ccb181"), 1))
        painter.drawRoundedRect(rect, 14, 14)
        color = "#fffbed" if active else INK
        font = QFont(self.font()); font.setPixelSize(ui_font_pixels(13)); font.setBold(True)
        painter.setFont(font)
        text_width = QFontMetrics(font).horizontalAdvance(self.text())
        x = max(8, (self.width()-text_width-28)/2)
        paint_symbol(painter, QRectF(x, (self.height()-21)/2-1, 21, 21), self.symbol, color)
        painter.setPen(QColor(color))
        painter.drawText(QRectF(x+28, 0, self.width()-x-30, self.height()-2), Qt.AlignmentFlag.AlignVCenter, self.text())
        if self.hasFocus():
            painter.setPen(QPen(QColor("#9e793c"), 1, Qt.PenStyle.DotLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(3, 3, -3, -3), 8, 8)
