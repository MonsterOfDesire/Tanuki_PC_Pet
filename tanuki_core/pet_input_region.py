from __future__ import annotations

from collections import OrderedDict

from PyQt6.QtCore import QRect
from PyQt6.QtGui import QBitmap, QRegion

from .pet_overlay_renderer import (
    compute_chorus_music_draw_spec,
    compute_log_icon_draw_spec,
    compute_star_draw_specs,
    should_show_chorus_audience_indicator,
    should_show_chorus_music_indicator,
)


def _frame_region(frame, *, flipped=False):
    bitmap = frame.mask()
    if flipped:
        bitmap = QBitmap.fromImage(bitmap.toImage().mirrored(True, False))
    return QRegion(bitmap)


def _overlay_region(pet, *, draw_y, overlay_scale):
    region = QRegion()
    widget_width = int(pet.width())

    if float(getattr(pet, "bar_opacity", 0.0) or 0.0) > 0.0:
        region |= QRegion(QRect((widget_width - 60) // 2, draw_y - 12, 60, 5))

    if bool(getattr(pet, "show_heart", False)):
        size = int(35 * overlay_scale)
        region |= QRegion(
            QRect(
                (widget_width - size) // 2,
                draw_y - 80,
                size,
                size + 60,
            )
        )

    if float(getattr(pet, "star_opacity", 0.0) or 0.0) > 0.0:
        for spec in compute_star_draw_specs(
            widget_width,
            draw_y,
            overlay_scale,
            0,
            0,
        ):
            region |= QRegion(
                QRect(spec.x, spec.y - 8, spec.size, spec.size + 16)
            )

    if bool(getattr(pet, "show_log_icon", False)):
        spec = compute_log_icon_draw_spec(
            widget_width,
            draw_y,
            overlay_scale,
            0,
        )
        region |= QRegion(
            QRect(spec.x, spec.y - 42, spec.size, spec.size + 42)
        )

    activity_state = getattr(pet, "activity_state", None)
    if (
        should_show_chorus_music_indicator(activity_state)
        or should_show_chorus_audience_indicator(activity_state)
    ):
        spec = compute_chorus_music_draw_spec(
            widget_width,
            draw_y,
            overlay_scale,
        )
        region |= QRegion(QRect(spec.x, spec.y, spec.size, spec.size))

    if bool(getattr(pet, "is_debug_enabled", lambda: False)()):
        region |= QRegion(QRect(0, 0, widget_width, max(1, draw_y)))
    elif bool(
        getattr(pet, "is_social_status_enabled", lambda: False)()
    ):
        region |= QRegion(
            QRect(0, max(0, draw_y - 90), widget_width, 90)
        )
    return region


class PetInputRegionController:
    def __init__(self, *, enabled=False, max_cached_frames=96):
        self.enabled = bool(enabled)
        self.max_cached_frames = max(1, int(max_cached_frames))
        self._frame_regions = OrderedDict()
        self._last_signature = None

    def _cached_frame_region(self, frame, *, flipped=False):
        key = (int(frame.cacheKey()), bool(flipped))
        cached = self._frame_regions.get(key)
        if cached is None:
            cached = _frame_region(frame, flipped=flipped)
            self._frame_regions[key] = cached
            while len(self._frame_regions) > self.max_cached_frames:
                self._frame_regions.popitem(last=False)
        else:
            self._frame_regions.move_to_end(key)
        return QRegion(cached)

    @staticmethod
    def _overlay_signature(pet):
        activity_state = getattr(pet, "activity_state", None)
        return (
            float(getattr(pet, "bar_opacity", 0.0) or 0.0) > 0.0,
            bool(getattr(pet, "show_heart", False)),
            float(getattr(pet, "star_opacity", 0.0) or 0.0) > 0.0,
            bool(getattr(pet, "show_log_icon", False)),
            should_show_chorus_music_indicator(activity_state),
            should_show_chorus_audience_indicator(activity_state),
            bool(getattr(pet, "is_debug_enabled", lambda: False)()),
            bool(
                getattr(
                    pet,
                    "is_social_status_enabled",
                    lambda: False,
                )()
            ),
        )

    def refresh(self, pet, *, force=False):
        if not self.enabled:
            return False
        frames = getattr(pet, "current_frames", ())
        if not frames:
            pet.clearMask()
            self._last_signature = None
            return True

        frame = frames[int(getattr(pet, "frame_index", 0)) % len(frames)]
        flipped = (
            int(getattr(pet, "direction", 1)) == 1
            if bool(getattr(pet, "original_face_left", True))
            else int(getattr(pet, "direction", 1)) == -1
        )
        overlay_signature = self._overlay_signature(pet)
        signature = (
            int(frame.cacheKey()),
            bool(flipped),
            int(pet.width()),
            int(pet.height()),
            overlay_signature,
        )
        if not force and signature == self._last_signature:
            return False

        draw_x = (int(pet.width()) - int(frame.width())) // 2
        draw_y = int(pet.height()) - int(frame.height())
        region = self._cached_frame_region(frame, flipped=flipped)
        region.translate(draw_x, draw_y)
        overlay_scale = max(
            1.0,
            float(getattr(pet, "display_scale_multiplier", 1.0)) ** 0.5,
        )
        region |= _overlay_region(
            pet,
            draw_y=draw_y,
            overlay_scale=overlay_scale,
        )
        pet.setMask(region)
        self._last_signature = signature
        return True
