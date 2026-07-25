from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QAbstractButton


class ToggleSwitch(QAbstractButton):
    """DPI-aware painted toggle used by settings and summon controls."""

    def __init__(self, parent=None, width=44, height=24):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(int(width), int(height))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName("開關")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        width = float(self.width())
        height = float(self.height())
        track_margin_y = max(2.0, height * 0.10)
        knob_margin = max(3.0, height * 0.18)
        knob_size = max(8.0, height - knob_margin * 2.0)
        if not self.isEnabled():
            track_color = QColor(120, 113, 106, 65)
            knob_color = QColor(255, 255, 255, 120)
        elif self.isChecked():
            track_color = QColor("#69b84f")
            knob_color = QColor("#fffdf7")
        else:
            track_color = QColor(120, 113, 106, 130)
            knob_color = QColor("#fffdf7")
        if self.underMouse() and self.isEnabled():
            track_color = track_color.lighter(112)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track_color)
        painter.drawRoundedRect(
            QRectF(
                1.0,
                track_margin_y,
                width - 2.0,
                height - track_margin_y * 2.0,
            ),
            height / 2.0,
            height / 2.0,
        )
        knob_x = (
            width - knob_margin - knob_size
            if self.isChecked()
            else knob_margin
        )
        painter.setBrush(knob_color)
        painter.drawEllipse(
            QRectF(
                knob_x,
                (height - knob_size) / 2.0,
                knob_size,
                knob_size,
            )
        )
        painter.end()
