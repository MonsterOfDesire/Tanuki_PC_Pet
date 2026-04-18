import math
from dataclasses import dataclass


@dataclass(frozen=True)
class StarSpriteSpec:
    x: int
    y: int
    size: int


@dataclass(frozen=True)
class DebugOverlayLayout:
    box_x: int
    box_width: int
    box_height: int


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


def compute_debug_overlay_layout(line_widths, line_height, max_debug_width, widget_width):
    box_height = (len(line_widths) * line_height) + 10
    box_width = min(max_debug_width, max(line_widths) + 12)
    box_x = max(4, (widget_width - box_width) // 2)
    return DebugOverlayLayout(box_x=box_x, box_width=box_width, box_height=box_height)


class PetOverlayRenderer:
    def draw_character(self, painter, widget_width, pixmap, draw_x, draw_y, should_flip):
        painter.save()
        if should_flip:
            painter.translate(widget_width, 0)
            painter.scale(-1, 1)
            painter.drawPixmap(widget_width - draw_x - pixmap.width(), draw_y, pixmap)
        else:
            painter.drawPixmap(draw_x, draw_y, pixmap)
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
