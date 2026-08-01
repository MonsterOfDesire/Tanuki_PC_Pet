import math
from dataclasses import dataclass


def clamp_whiteness(value):
    return max(0.0, min(1.0, float(value or 0.0)))


@dataclass(frozen=True)
class StarSpriteSpec:
    x: int
    y: int
    size: int


@dataclass(frozen=True)
class IconSpriteSpec:
    x: int
    y: int
    size: int


@dataclass(frozen=True)
class DebugOverlayLayout:
    box_x: int
    box_width: int
    box_height: int


@dataclass(frozen=True)
class HeadStatusLabelLayout:
    x: int
    y: int
    width: int
    height: int


def compute_star_draw_specs(widget_width, draw_y, overlay_scale, star_y_offset, star_anim_counter, num_stars=3):
    size = int(25 * overlay_scale)
    spacing = int(30 * overlay_scale)
    start_x = (widget_width - (num_stars * size)) // 2
    base_y = draw_y - 50 + star_y_offset
    specs = []
    for index in range(num_stars):
        individual_offset = int(math.sin((star_anim_counter + index * 20) * 0.1) * 3)
        specs.append(
            StarSpriteSpec(
                x=start_x + (index * spacing),
                y=base_y + individual_offset,
                size=size,
            )
        )
    return tuple(specs)


def compute_log_icon_draw_spec(widget_width, draw_y, overlay_scale, log_icon_y_offset):
    size = int(34 * overlay_scale)
    x = (widget_width - size) // 2 + int(36 * overlay_scale)
    y = draw_y - 26 - int(log_icon_y_offset)
    return IconSpriteSpec(x=x, y=y, size=size)


def compute_debug_overlay_layout(line_widths, line_height, max_debug_width, widget_width):
    box_height = (len(line_widths) * line_height) + 10
    box_width = min(max_debug_width, max(line_widths) + 12)
    box_x = max(4, (widget_width - box_width) // 2)
    return DebugOverlayLayout(box_x=box_x, box_width=box_width, box_height=box_height)


def compute_head_status_label_layout(widget_width, draw_y, text_width, line_height):
    width = min(max(64, int(text_width) + 16), max(64, int(widget_width) - 8))
    height = int(line_height) + 8
    x = max(4, (int(widget_width) - width) // 2)
    y = max(4, int(draw_y) - height - 24)
    return HeadStatusLabelLayout(x=x, y=y, width=width, height=height)


class PetOverlayRenderer:
    def draw_character(
        self,
        painter,
        widget_width,
        pixmap,
        draw_x,
        draw_y,
        should_flip,
        whiteness=0.0,
    ):
        painter.save()
        if should_flip:
            painter.translate(widget_width, 0)
            painter.scale(-1, 1)
            painter.drawPixmap(widget_width - draw_x - pixmap.width(), draw_y, pixmap)
        else:
            painter.drawPixmap(draw_x, draw_y, pixmap)
        painter.restore()
        whiteness = clamp_whiteness(whiteness)
        if whiteness <= 0.0:
            return
        from PyQt6.QtGui import QColor, QPainter

        painter.save()
        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_SourceAtop
        )
        painter.setOpacity(whiteness)
        overlay_x = (
            widget_width - draw_x - pixmap.width()
            if should_flip
            else draw_x
        )
        painter.fillRect(
            overlay_x,
            draw_y,
            pixmap.width(),
            pixmap.height(),
            QColor(255, 255, 255),
        )
        painter.restore()

    def draw_mood_bar(self, painter, widget_width, draw_y, mood_score, opacity):
        if opacity <= 0:
            return
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QColor

        painter.setOpacity(opacity)
        bar_width, bar_height = 60, 5
        bar_x = (widget_width - bar_width) // 2
        bar_y = draw_y - 12
        painter.setBrush(QColor(0, 0, 0, 120))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(bar_x, bar_y, bar_width, bar_height, 2, 2)
        color = QColor(255, 50, 50) if mood_score < 20 else QColor(255, 200, 50) if mood_score < 50 else QColor(80, 255, 80)
        painter.setBrush(color)
        painter.drawRoundedRect(bar_x, bar_y, int(bar_width * (mood_score / 100)), bar_height, 2, 2)

    def draw_heart(self, painter, widget_width, draw_y, overlay_scale, heart_pixmap, show_heart, heart_opacity, heart_y_offset):
        if not show_heart or heart_pixmap.isNull():
            return
        painter.setOpacity(heart_opacity)
        heart_size = int(35 * overlay_scale)
        painter.drawPixmap(
            (widget_width - heart_size) // 2,
            draw_y - 20 - heart_y_offset,
            heart_size,
            heart_size,
            heart_pixmap,
        )

    def draw_stars(self, painter, widget_width, draw_y, overlay_scale, star_pixmap, star_opacity, star_y_offset, star_anim_counter):
        if star_opacity <= 0 or star_pixmap.isNull():
            return
        painter.setOpacity(star_opacity)
        for spec in compute_star_draw_specs(widget_width, draw_y, overlay_scale, star_y_offset, star_anim_counter):
            painter.drawPixmap(spec.x, spec.y, spec.size, spec.size, star_pixmap)

    def draw_log_icon(self, painter, widget_width, draw_y, overlay_scale, log_icon_pixmap, show_log_icon, log_icon_opacity, log_icon_y_offset):
        if not show_log_icon or log_icon_pixmap.isNull():
            return
        painter.setOpacity(log_icon_opacity)
        spec = compute_log_icon_draw_spec(widget_width, draw_y, overlay_scale, log_icon_y_offset)
        painter.drawPixmap(spec.x, spec.y, spec.size, spec.size, log_icon_pixmap)

    def draw_head_status_label(self, painter, label_text, widget_width, draw_y):
        label_text = str(label_text or "").strip()
        if not label_text:
            return
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QColor

        metrics = painter.fontMetrics()
        layout = compute_head_status_label_layout(
            widget_width,
            draw_y,
            metrics.horizontalAdvance(label_text),
            metrics.height(),
        )
        painter.setOpacity(1.0)
        painter.setBrush(QColor(10, 10, 10, 190))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(layout.x, layout.y, layout.width, layout.height, 6, 6)
        painter.setPen(QColor(230, 255, 230))
        painter.drawText(
            layout.x,
            layout.y,
            layout.width,
            layout.height,
            Qt.AlignmentFlag.AlignCenter,
            label_text,
        )

    def draw_debug_overlay(self, painter, lines, max_debug_width, widget_width):
        if not lines:
            return
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QColor

        metrics = painter.fontMetrics()
        line_height = metrics.height()
        line_widths = tuple(metrics.horizontalAdvance(line) for line in lines)
        layout = compute_debug_overlay_layout(line_widths, line_height, max_debug_width, widget_width)
        painter.setBrush(QColor(10, 10, 10, 170))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(layout.box_x, 4, layout.box_width, layout.box_height, 6, 6)
        painter.setPen(QColor(210, 255, 210))
        for index, line in enumerate(lines):
            painter.drawText(layout.box_x + 6, 8 + line_height + (index * line_height), line)
