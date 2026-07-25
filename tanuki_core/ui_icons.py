from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
)


METRIC_COLORS = {
    "familiarity": "#3f96d1",
    "trust": "#69b84f",
    "attachment": "#e96494",
    "tension": "#ef8b2c",
}

EVENT_CHANNEL_COLORS = {
    "social": "#a8d47a",
    "economy": "#75bcea",
    "item": "#b89aea",
    "story": "#e8b765",
    "system": "#b8c9c3",
}


def create_metric_icon(metric_kind, size=16):
    """Return the canonical relationship metric icon used across UI pages."""

    color = QColor(METRIC_COLORS[metric_kind])
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    scale = size / 16.0
    if metric_kind == "familiarity":
        painter.drawEllipse(QRectF(5 * scale, 1 * scale, 6 * scale, 6 * scale))
        painter.drawRoundedRect(QRectF(3 * scale, 8 * scale, 10 * scale, 7 * scale), 3, 3)
    elif metric_kind == "trust":
        path = QPainterPath()
        path.moveTo(8 * scale, 1 * scale)
        path.lineTo(14 * scale, 4 * scale)
        path.lineTo(13 * scale, 10 * scale)
        path.quadTo(11 * scale, 14 * scale, 8 * scale, 15 * scale)
        path.quadTo(5 * scale, 14 * scale, 3 * scale, 10 * scale)
        path.lineTo(2 * scale, 4 * scale)
        path.closeSubpath()
        painter.drawPath(path)
    elif metric_kind == "attachment":
        path = QPainterPath()
        path.moveTo(8 * scale, 14 * scale)
        path.cubicTo(-1 * scale, 8 * scale, 2 * scale, 1 * scale, 8 * scale, 5 * scale)
        path.cubicTo(14 * scale, 1 * scale, 17 * scale, 8 * scale, 8 * scale, 14 * scale)
        painter.drawPath(path)
    elif metric_kind == "tension":
        painter.drawPolygon(
            QPolygonF(
                (
                    QPointF(9 * scale, 0),
                    QPointF(3 * scale, 9 * scale),
                    QPointF(8 * scale, 9 * scale),
                    QPointF(6 * scale, 16 * scale),
                    QPointF(14 * scale, 6 * scale),
                    QPointF(9 * scale, 6 * scale),
                )
            )
        )
    painter.end()
    return QIcon(pixmap)


def create_ui_pixmap(name, color="#fffaf2", size=18):
    """Paint a small DPI-aware monochrome icon without external bitmap assets."""

    size = max(12, int(size))
    normalized_name = str(name or "info")
    if normalized_name in METRIC_COLORS:
        return create_metric_icon(normalized_name, size=size).pixmap(size, size)
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.scale(size / 20.0, size / 20.0)
    icon_color = QColor(color)
    pen = QPen(icon_color, 1.7)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    if normalized_name == "all":
        for y in (5.0, 10.0, 15.0):
            painter.setBrush(QBrush(icon_color))
            painter.drawEllipse(QPointF(4.0, y), 1.2, 1.2)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawLine(QPointF(7.0, y), QPointF(16.0, y))
    elif normalized_name in {"personal", "participants"}:
        _paint_person(painter, icon_color, center_x=10.0)
    elif normalized_name in {"social", "relationship", "relationship_familiarity"}:
        _paint_person(painter, icon_color, center_x=7.0, scale=0.82)
        _paint_person(painter, icon_color, center_x=13.0, scale=0.82)
    elif normalized_name in {"economy", "living_fund"}:
        painter.setBrush(QBrush(icon_color))
        painter.drawEllipse(QRectF(2.5, 2.5, 15.0, 15.0))
        painter.setPen(QPen(QColor("#174536"), 1.5))
        font = QFont()
        font.setBold(True)
        font.setPixelSize(10)
        painter.setFont(font)
        painter.drawText(QRectF(3.0, 2.0, 14.0, 16.0), Qt.AlignmentFlag.AlignCenter, "$")
    elif normalized_name == "item":
        painter.setBrush(QBrush(icon_color))
        painter.drawPolygon(
            QPolygonF(
                (
                    QPointF(3.0, 6.5),
                    QPointF(10.0, 3.0),
                    QPointF(17.0, 6.5),
                    QPointF(10.0, 10.0),
                )
            )
        )
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPolygon(
            QPolygonF(
                (
                    QPointF(3.0, 6.5),
                    QPointF(10.0, 10.0),
                    QPointF(17.0, 6.5),
                    QPointF(17.0, 14.0),
                    QPointF(10.0, 17.5),
                    QPointF(3.0, 14.0),
                )
            )
        )
        painter.drawLine(QPointF(10.0, 10.0), QPointF(10.0, 17.5))
    elif normalized_name == "system":
        painter.drawEllipse(QRectF(6.0, 6.0, 8.0, 8.0))
        painter.drawEllipse(QRectF(8.5, 8.5, 3.0, 3.0))
        for start, end in (
            ((10, 2), (10, 5)),
            ((10, 15), (10, 18)),
            ((2, 10), (5, 10)),
            ((15, 10), (18, 10)),
            ((4.3, 4.3), (6.4, 6.4)),
            ((13.6, 13.6), (15.7, 15.7)),
            ((15.7, 4.3), (13.6, 6.4)),
            ((6.4, 13.6), (4.3, 15.7)),
        ):
            painter.drawLine(QPointF(*start), QPointF(*end))
    elif normalized_name == "story":
        painter.drawRoundedRect(QRectF(3.0, 3.5, 6.7, 13.0), 1.0, 1.0)
        painter.drawRoundedRect(QRectF(10.3, 3.5, 6.7, 13.0), 1.0, 1.0)
        painter.drawLine(QPointF(10.0, 4.5), QPointF(10.0, 16.0))
    elif normalized_name == "detach":
        painter.drawRoundedRect(QRectF(2.5, 7.0, 10.5, 10.5), 1.2, 1.2)
        painter.drawLine(QPointF(8.5, 11.5), QPointF(17.0, 3.0))
        painter.drawLine(QPointF(10.5, 3.0), QPointF(17.0, 3.0))
        painter.drawLine(QPointF(17.0, 3.0), QPointF(17.0, 9.5))
    elif normalized_name == "time":
        painter.drawEllipse(QRectF(2.5, 2.5, 15.0, 15.0))
        painter.drawLine(QPointF(10.0, 5.5), QPointF(10.0, 10.0))
        painter.drawLine(QPointF(10.0, 10.0), QPointF(13.5, 12.0))
    elif normalized_name == "tag":
        path = QPainterPath()
        path.moveTo(2.5, 5.0)
        path.lineTo(10.5, 2.5)
        path.lineTo(17.5, 9.5)
        path.lineTo(10.0, 17.0)
        path.lineTo(2.5, 9.5)
        path.closeSubpath()
        painter.drawPath(path)
        painter.setBrush(QBrush(icon_color))
        painter.drawEllipse(QPointF(7.0, 6.2), 1.3, 1.3)
    elif normalized_name == "mood":
        _paint_heart(painter, icon_color)
    elif normalized_name in {"attachment", "relationship_attachment"}:
        _paint_heart(painter, icon_color)
    elif normalized_name in {"trust", "relationship_trust"}:
        painter.setBrush(QBrush(icon_color))
        painter.drawPolygon(
            QPolygonF(
                (
                    QPointF(10.0, 2.0),
                    QPointF(16.0, 4.5),
                    QPointF(15.0, 12.5),
                    QPointF(10.0, 18.0),
                    QPointF(5.0, 12.5),
                    QPointF(4.0, 4.5),
                )
            )
        )
    elif normalized_name in {"tension", "relationship_tension"}:
        painter.setBrush(QBrush(icon_color))
        painter.drawPolygon(
            QPolygonF(
                (
                    QPointF(11.0, 1.5),
                    QPointF(4.5, 11.0),
                    QPointF(9.0, 11.0),
                    QPointF(7.8, 18.5),
                    QPointF(15.5, 8.5),
                    QPointF(11.0, 8.5),
                )
            )
        )
    elif normalized_name == "household_pressure":
        painter.drawArc(QRectF(2.5, 4.0, 15.0, 15.0), 0, 180 * 16)
        painter.drawLine(QPointF(10.0, 11.5), QPointF(14.5, 7.5))
        painter.setBrush(QBrush(icon_color))
        painter.drawEllipse(QPointF(10.0, 11.5), 1.4, 1.4)
    elif normalized_name == "achievement":
        painter.setBrush(QBrush(icon_color))
        painter.drawRoundedRect(QRectF(6.0, 2.0, 8.0, 9.0), 1.5, 1.5)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(QRectF(2.0, 3.0, 7.0, 7.0), 90 * 16, 180 * 16)
        painter.drawArc(QRectF(11.0, 3.0, 7.0, 7.0), -90 * 16, 180 * 16)
        painter.drawLine(QPointF(10.0, 11.0), QPointF(10.0, 15.0))
        painter.drawLine(QPointF(6.5, 18.0), QPointF(13.5, 18.0))
        painter.drawRoundedRect(QRectF(7.0, 15.0, 6.0, 2.5), 0.8, 0.8)
    elif normalized_name == "power":
        painter.drawArc(
            QRectF(3.0, 3.0, 14.0, 14.0),
            42 * 16,
            276 * 16,
        )
        painter.drawLine(QPointF(10.0, 1.5), QPointF(10.0, 10.0))
    elif normalized_name == "pin":
        path = QPainterPath()
        path.moveTo(6.0, 3.0)
        path.lineTo(14.0, 3.0)
        path.lineTo(12.8, 8.0)
        path.lineTo(15.5, 11.0)
        path.lineTo(10.8, 11.0)
        path.lineTo(10.0, 18.0)
        path.lineTo(9.2, 11.0)
        path.lineTo(4.5, 11.0)
        path.lineTo(7.2, 8.0)
        path.closeSubpath()
        painter.drawPath(path)
    else:
        painter.drawEllipse(QRectF(2.5, 2.5, 15.0, 15.0))
        painter.setBrush(QBrush(icon_color))
        painter.drawEllipse(QPointF(10.0, 6.0), 1.0, 1.0)
        painter.drawRoundedRect(QRectF(9.0, 9.0, 2.0, 5.5), 1.0, 1.0)

    painter.end()
    return pixmap


def create_ui_icon(name, color="#fffaf2", size=18):
    return QIcon(create_ui_pixmap(name, color=color, size=size))


def _paint_person(painter, color, center_x=10.0, scale=1.0):
    painter.setBrush(QBrush(color))
    painter.drawEllipse(
        QPointF(center_x, 5.3),
        3.0 * scale,
        3.0 * scale,
    )
    path = QPainterPath()
    path.moveTo(center_x - 5.0 * scale, 16.5)
    path.cubicTo(
        center_x - 4.5 * scale,
        10.0,
        center_x + 4.5 * scale,
        10.0,
        center_x + 5.0 * scale,
        16.5,
    )
    path.closeSubpath()
    painter.fillPath(path, QBrush(color))
    painter.setBrush(Qt.BrushStyle.NoBrush)


def _paint_heart(painter, color):
    path = QPainterPath()
    path.moveTo(10.0, 17.0)
    path.cubicTo(8.0, 14.5, 3.0, 11.0, 3.0, 7.0)
    path.cubicTo(3.0, 3.0, 8.0, 2.0, 10.0, 5.5)
    path.cubicTo(12.0, 2.0, 17.0, 3.0, 17.0, 7.0)
    path.cubicTo(17.0, 11.0, 12.0, 14.5, 10.0, 17.0)
    painter.fillPath(path, QBrush(color))
