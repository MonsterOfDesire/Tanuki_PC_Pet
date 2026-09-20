from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import re
from pathlib import Path

from PyQt6.QtCore import QRect, QSize, Qt
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QApplication

from .runtime_debug_log import log_suppressed_exception


ACHIEVEMENT_MEMORY_DIRECTORY = "achievement_memories"
CAPTURE_FILENAME = "capture.png"
METADATA_FILENAME = "metadata.json"
MAX_CAPTURE_PIXELS = 16_000_000
SCENE_CAPTURE_MARGIN_PX = 120
MAX_PERFORMING_CANDIDATES = 96
MAX_PARTICIPANT_MATCH_AGE_SECONDS = 30.0


@dataclass(frozen=True)
class VirtualDesktopCapture:
    image: QImage
    virtual_rect: QRect


def _safe_path_component(value):
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "").strip())
    return value.strip("._") or "unknown"


def capture_virtual_desktop_frame(*, screens=None):
    """Capture and compose all Qt screens in logical desktop coordinates."""
    screens = tuple(QApplication.screens() if screens is None else screens)
    if not screens:
        return None
    virtual_rect = QRect(screens[0].geometry())
    for screen in screens[1:]:
        virtual_rect = virtual_rect.united(screen.geometry())
    if virtual_rect.width() <= 0 or virtual_rect.height() <= 0:
        return None

    image = QImage(
        virtual_rect.size(),
        QImage.Format.Format_ARGB32_Premultiplied,
    )
    image.fill(Qt.GlobalColor.black)
    painter = QPainter(image)
    painted = False
    for screen in screens:
        pixmap = screen.grabWindow(0)
        if pixmap.isNull():
            continue
        geometry = screen.geometry()
        target = QRect(
            geometry.x() - virtual_rect.x(),
            geometry.y() - virtual_rect.y(),
            geometry.width(),
            geometry.height(),
        )
        painter.drawPixmap(target, pixmap)
        painted = True
    painter.end()
    if not painted:
        return None

    pixel_count = image.width() * image.height()
    if pixel_count > MAX_CAPTURE_PIXELS:
        ratio = (MAX_CAPTURE_PIXELS / float(pixel_count)) ** 0.5
        image = image.scaled(
            max(1, int(image.width() * ratio)),
            max(1, int(image.height() * ratio)),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    return VirtualDesktopCapture(image=image, virtual_rect=virtual_rect)


def capture_virtual_desktop_image(*, screens=None):
    frame = capture_virtual_desktop_frame(screens=screens)
    return frame.image if frame is not None else None


def crop_virtual_desktop_rect(frame, scene_rect):
    if frame is None:
        return None
    scene_rect = QRect(scene_rect).intersected(frame.virtual_rect)
    if scene_rect.isEmpty():
        return None
    scale_x = frame.image.width() / float(max(1, frame.virtual_rect.width()))
    scale_y = frame.image.height() / float(max(1, frame.virtual_rect.height()))
    image_rect = QRect(
        int(round((scene_rect.x() - frame.virtual_rect.x()) * scale_x)),
        int(round((scene_rect.y() - frame.virtual_rect.y()) * scale_y)),
        max(1, int(round(scene_rect.width() * scale_x))),
        max(1, int(round(scene_rect.height() * scale_y))),
    ).intersected(frame.image.rect())
    return frame.image.copy(image_rect) if not image_rect.isEmpty() else None


def capture_virtual_desktop_rect_image(scene_rect, output_size=None, *, screens=None):
    image = crop_virtual_desktop_rect(
        capture_virtual_desktop_frame(screens=screens),
        scene_rect,
    )
    if image is None or output_size is None:
        return image
    output_size = output_size if isinstance(output_size, QSize) else QSize(output_size)
    if output_size.isEmpty() or image.size() == output_size:
        return image
    return image.scaled(
        output_size,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def visible_pet_rect(pet):
    frames = tuple(getattr(pet, "current_frames", ()) or ())
    if not frames:
        return QRect(int(pet.x()), int(pet.y()), int(pet.width()), int(pet.height()))
    frame = frames[int(getattr(pet, "frame_index", 0)) % len(frames)]
    draw_x = (int(pet.width()) - int(frame.width())) // 2
    draw_y = int(pet.height()) - int(frame.height())
    return QRect(
        int(pet.x()) + draw_x,
        int(pet.y()) + draw_y,
        int(frame.width()),
        int(frame.height()),
    )


def crop_virtual_desktop_frame(frame, pets, *, margin=SCENE_CAPTURE_MARGIN_PX):
    if frame is None:
        return None
    rects = []
    for pet in pets or ():
        if pet is None or not bool(getattr(pet, "user_visible", True)):
            continue
        try:
            if not pet.isVisible():
                continue
        except Exception as error:
            log_suppressed_exception(
                "achievement_memory.pet_visibility",
                error,
            )
        rects.append(visible_pet_rect(pet))
    if not rects:
        return frame.image
    scene_rect = QRect(rects[0])
    for rect in rects[1:]:
        scene_rect = scene_rect.united(rect)
    scene_rect.adjust(-int(margin), -int(margin), int(margin), int(margin))
    scene_rect = scene_rect.intersected(frame.virtual_rect)
    if scene_rect.isEmpty():
        return frame.image
    return crop_virtual_desktop_rect(frame, scene_rect)


def capture_pet_scene_image(pets, *, screens=None, margin=SCENE_CAPTURE_MARGIN_PX):
    return crop_virtual_desktop_frame(
        capture_virtual_desktop_frame(screens=screens),
        pets,
        margin=margin,
    )


class AchievementMemoryCaptureService:
    """Stores one opt-in screenshot for each achievement's first unlock."""

    def __init__(
        self,
        data_directory,
        *,
        image_provider=None,
        now_provider=None,
    ):
        self.root = Path(data_directory) / ACHIEVEMENT_MEMORY_DIRECTORY
        self.image_provider = image_provider or capture_virtual_desktop_image
        self.now_provider = now_provider or (
            lambda: datetime.now(timezone.utc)
        )
        self._performing_candidates = {}
        self._latest_performing_candidates = {}
        self._latest_performing_candidate = None

    def stage_performing_candidate(self, kind, image, *, metadata=None):
        kind = str(kind or "").strip()
        if (
            not kind
            or image is None
            or bool(getattr(image, "isNull", lambda: True)())
        ):
            return False
        metadata = dict(metadata or {})
        candidate = (
            image.copy() if hasattr(image, "copy") else image,
            metadata,
        )
        capture_key = _candidate_capture_key(metadata)
        storage_key = (kind, capture_key)
        self._performing_candidates.pop(storage_key, None)
        self._performing_candidates[storage_key] = candidate
        while len(self._performing_candidates) > MAX_PERFORMING_CANDIDATES:
            self._performing_candidates.pop(next(iter(self._performing_candidates)))
        self._latest_performing_candidates[kind] = candidate
        self._latest_performing_candidate = candidate
        return True

    def discard_performing_candidates(self):
        """Forget frames that may belong to a speed-ineligible scene."""
        self._performing_candidates.clear()
        self._latest_performing_candidates.clear()
        self._latest_performing_candidate = None

    @staticmethod
    def capture_target_names(capture_context):
        details = _capture_context_details(capture_context)
        return (
            details["participant_names"]
            if details is not None
            else frozenset()
        )

    @staticmethod
    def _candidate_kind_for_achievement(achievement_id):
        prefix = str(achievement_id or "").partition(".")[0]
        return {
            "race": "race",
            "chorus": "chorus",
            "sleep": "sleep",
            "transformation": "transformation",
            "care": "care",
            "honey": "honey_guard",
            "food": "food",
            "work": "work",
            "ambient": "ambient",
            "activity": "activity",
        }.get(prefix, "")

    def capture(
        self,
        achievement_ids,
        *,
        world_mode,
        fallback_image=None,
        capture_context=None,
    ):
        pending = []
        for achievement_id in dict.fromkeys(
            str(item or "").strip() for item in (achievement_ids or ())
        ):
            if not achievement_id:
                continue
            path = self.capture_path(world_mode, achievement_id)
            if not path.exists():
                pending.append((achievement_id, path))
        if not pending:
            return ()
        captured_at = self.now_provider()
        if isinstance(captured_at, datetime):
            captured_at_text = captured_at.astimezone(timezone.utc).isoformat()
        else:
            captured_at_text = str(captured_at)
        saved = []
        unlock_image = fallback_image
        unlock_image_loaded = fallback_image is not None
        for achievement_id, path in pending:
            candidate_kind = self._candidate_kind_for_achievement(
                achievement_id
            )
            candidate = self._candidate_for_context(
                candidate_kind,
                capture_context,
            )
            if candidate is None:
                if not unlock_image_loaded:
                    try:
                        unlock_image = self.image_provider()
                    except Exception as error:
                        log_suppressed_exception(
                            "achievement_memory.image_provider",
                            error,
                        )
                        continue
                    unlock_image_loaded = True
                image = unlock_image
                candidate_metadata = {}
            else:
                image, candidate_metadata = candidate
            if image is None or bool(getattr(image, "isNull", lambda: True)()):
                continue
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                if not bool(image.save(str(path), "PNG")):
                    continue
                metadata = {
                    "achievement_id": achievement_id,
                    "world_mode": str(world_mode or "sandbox"),
                    "captured_at": captured_at_text,
                    "image": CAPTURE_FILENAME,
                    "capture_moment": (
                        "performing" if candidate is not None else "unlock"
                    ),
                    "scene": dict(candidate_metadata),
                }
                (path.parent / METADATA_FILENAME).write_text(
                    json.dumps(metadata, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                saved.append(path)
            except Exception as error:
                log_suppressed_exception(
                    "achievement_memory.save_capture",
                    error,
                )
                continue
        return tuple(saved)

    def _candidate_for_context(self, candidate_kind, capture_context):
        details = _capture_context_details(capture_context)
        if details is None:
            if candidate_kind == "activity":
                return self._latest_performing_candidate
            return self._latest_performing_candidates.get(candidate_kind)

        event_kind = _candidate_kind_for_event(details["event_name"])
        if candidate_kind == "activity" and event_kind:
            candidate_kind = event_kind
        activity_id = details["activity_id"]
        if activity_id:
            candidate = self._performing_candidates.get(
                (candidate_kind, activity_id)
            )
            if candidate is not None:
                return candidate

        participant_names = details["participant_names"]
        if not participant_names:
            return None
        for (kind, _capture_key), candidate in reversed(
            tuple(self._performing_candidates.items())
        ):
            if kind != candidate_kind:
                continue
            candidate_names = frozenset(
                str(name or "").strip()
                for name in candidate[1].get("participants", ())
                if str(name or "").strip()
            )
            captured_at = _safe_float(candidate[1].get("captured_at"), 0.0)
            occurred_at = details["occurred_at"]
            recent_enough = (
                captured_at <= 0.0
                or occurred_at <= 0.0
                or abs(occurred_at - captured_at)
                <= MAX_PARTICIPANT_MATCH_AGE_SECONDS
            )
            if candidate_names == participant_names and recent_enough:
                return candidate
        return None

    def capture_path(self, world_mode, achievement_id):
        return (
            self.root
            / _safe_path_component(world_mode)
            / _safe_path_component(achievement_id)
            / CAPTURE_FILENAME
        )

    def latest_capture_path(self, world_mode, achievement_id):
        path = self.capture_path(world_mode, achievement_id)
        return path if path.is_file() else None

    def clear_capture(self, world_mode, achievement_id):
        """Remove only the known screenshot files for one achievement."""
        capture_path = self.capture_path(world_mode, achievement_id)
        directory = capture_path.parent
        removed = False
        for path in (
            capture_path,
            directory / METADATA_FILENAME,
        ):
            try:
                if path.is_file():
                    path.unlink()
                    removed = True
            except OSError as error:
                log_suppressed_exception(
                    "achievement_memory.clear_capture_file",
                    error,
                )
                continue
        try:
            directory.rmdir()
        except OSError as error:
            if directory.exists():
                log_suppressed_exception(
                    "achievement_memory.clear_capture_directory",
                    error,
                )
        return removed


def _candidate_capture_key(metadata):
    activity_id = str(metadata.get("activity_id", "") or "").strip()
    if activity_id:
        return activity_id
    scene_key = str(metadata.get("scene_key", "") or "").strip()
    if scene_key:
        return scene_key
    participants = tuple(
        sorted(
            str(name or "").strip()
            for name in metadata.get("participants", ())
            if str(name or "").strip()
        )
    )
    return "participants:" + "|".join(participants)


def _capture_context_details(capture_context):
    if capture_context is None:
        return None
    if isinstance(capture_context, Mapping):
        event_name = str(capture_context.get("event_name", "") or "")
        payload = capture_context.get("payload", capture_context)
        participants = capture_context.get("participants", ())
        occurred_at = _safe_float(capture_context.get("occurred_at"), 0.0)
    else:
        event_name = str(getattr(capture_context, "event_name", "") or "")
        payload = getattr(capture_context, "payload", {})
        participants = getattr(capture_context, "participants", ())
        occurred_at = _safe_float(
            getattr(capture_context, "occurred_at", 0.0),
            0.0,
        )
    payload = dict(payload or {}) if isinstance(payload, Mapping) else {}
    if not participants:
        participants = payload.get("activity_participants", ())
    participant_names = {
        str(participant.get("name", "") or "").strip()
        for participant in (participants or ())
        if isinstance(participant, Mapping)
        and str(participant.get("name", "") or "").strip()
    }
    for field_name in (
        "character_name",
        "caregiver_name",
        "target_name",
        "challenger_name",
        "opponent_name",
    ):
        name = str(payload.get(field_name, "") or "").strip()
        if name:
            participant_names.add(name)
    for field_name in (
        "naturally_sleeping_character_names",
        "performer_names",
        "audience_names",
    ):
        values = payload.get(field_name, ())
        if not isinstance(values, (list, tuple, set, frozenset)):
            continue
        participant_names.update(
            str(name or "").strip()
            for name in values
            if str(name or "").strip()
        )
    return {
        "event_name": event_name,
        "activity_id": str(payload.get("activity_id", "") or "").strip(),
        "participant_names": frozenset(participant_names),
        "occurred_at": occurred_at,
    }


def _candidate_kind_for_event(event_name):
    event_name = str(event_name or "")
    if event_name.startswith("activity.race."):
        return "race"
    if event_name.startswith("activity.chorus."):
        return "chorus"
    if event_name.startswith("activity.sleep."):
        return "sleep"
    if event_name.startswith("activity.work."):
        return "work"
    if event_name.startswith("activity.transformation."):
        return "transformation"
    if event_name.startswith("interaction.care."):
        return "care"
    if event_name.startswith("interaction.honey_guard."):
        return "honey_guard"
    if event_name.startswith("interaction.food_share."):
        return "food"
    if event_name.startswith("ambient."):
        return "ambient"
    return ""


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)
