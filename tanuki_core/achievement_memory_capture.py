from __future__ import annotations

from datetime import datetime, timezone
import json
import re
from pathlib import Path

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QApplication


ACHIEVEMENT_MEMORY_DIRECTORY = "achievement_memories"
CAPTURE_FILENAME = "capture.png"
METADATA_FILENAME = "metadata.json"
MAX_CAPTURE_PIXELS = 16_000_000


def _safe_path_component(value):
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "").strip())
    return value.strip("._") or "unknown"


def capture_virtual_desktop_image(*, screens=None):
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
    return image


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

    def capture(self, achievement_ids, *, world_mode):
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
        try:
            image = self.image_provider()
        except Exception:
            return ()
        if image is None or bool(getattr(image, "isNull", lambda: True)()):
            return ()

        captured_at = self.now_provider()
        if isinstance(captured_at, datetime):
            captured_at_text = captured_at.astimezone(timezone.utc).isoformat()
        else:
            captured_at_text = str(captured_at)
        saved = []
        for achievement_id, path in pending:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                if not bool(image.save(str(path), "PNG")):
                    continue
                metadata = {
                    "achievement_id": achievement_id,
                    "world_mode": str(world_mode or "sandbox"),
                    "captured_at": captured_at_text,
                    "image": CAPTURE_FILENAME,
                }
                (path.parent / METADATA_FILENAME).write_text(
                    json.dumps(metadata, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                saved.append(path)
            except Exception:
                continue
        return tuple(saved)

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
