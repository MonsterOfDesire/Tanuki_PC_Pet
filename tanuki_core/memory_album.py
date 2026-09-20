from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import math
from pathlib import Path

from .runtime_debug_log import log_suppressed_exception


MEMORY_ALBUM_DIRECTORY = "memory_album"
MEMORY_ALBUM_INDEX_FILENAME = "index.json"
MEMORY_ALBUM_MODES = ("off", "events", "random")
MEMORY_ALBUM_CAPACITIES = (20, 50, 100)
MEMORY_ALBUM_WARNING_RATIO = 0.8


@dataclass(frozen=True)
class MemoryAlbumEntry:
    path: Path
    captured_at: str
    kind: str = ""
    participants: tuple[str, ...] = ()


@dataclass(frozen=True)
class MemoryAlbumSnapshot:
    mode: str
    capacity: int
    count: int
    entries: tuple[MemoryAlbumEntry, ...]

    @property
    def full(self):
        return self.count >= self.capacity

    @property
    def near_full(self):
        return (
            not self.full
            and self.count >= math.ceil(self.capacity * MEMORY_ALBUM_WARNING_RATIO)
        )


def normalize_memory_album_mode(value):
    value = str(value or "off")
    return value if value in MEMORY_ALBUM_MODES else "off"


def normalize_memory_album_capacity(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = MEMORY_ALBUM_CAPACITIES[0]
    return value if value in MEMORY_ALBUM_CAPACITIES else MEMORY_ALBUM_CAPACITIES[0]


class MemoryAlbumService:
    """Saves opt-in memories without ever deleting an existing photograph."""

    def __init__(self, data_directory, *, now_provider=None):
        self.root = Path(data_directory) / MEMORY_ALBUM_DIRECTORY
        self.index_path = self.root / MEMORY_ALBUM_INDEX_FILENAME
        self.now_provider = now_provider or (lambda: datetime.now().astimezone())

    def snapshot(self, *, mode, capacity):
        normalized_mode = normalize_memory_album_mode(mode)
        normalized_capacity = normalize_memory_album_capacity(capacity)
        entries = self._load_entries()
        return MemoryAlbumSnapshot(
            mode=normalized_mode,
            capacity=normalized_capacity,
            count=len(entries),
            entries=entries,
        )

    def capture(self, image, *, mode, capacity, kind="", participants=()):
        snapshot = self.snapshot(mode=mode, capacity=capacity)
        if snapshot.mode == "off" or snapshot.full:
            return None
        return self._save_capture(
            image,
            snapshot=snapshot,
            kind=kind,
            participants=participants,
        )

    def capture_manual(self, image, *, capacity, kind="manual", participants=()):
        """Save an explicit user photo even when automatic capture is off."""
        snapshot = self.snapshot(mode="events", capacity=capacity)
        if snapshot.full:
            return None
        return self._save_capture(
            image,
            snapshot=snapshot,
            kind=kind,
            participants=participants,
        )

    def _save_capture(self, image, *, snapshot, kind="", participants=()):
        if image is None or bool(getattr(image, "isNull", lambda: True)()):
            return None
        captured_at = self.now_provider()
        if not isinstance(captured_at, datetime):
            captured_at = datetime.now().astimezone()
        if captured_at.tzinfo is None:
            captured_at = captured_at.astimezone()
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._available_timestamp_path(captured_at)
        try:
            if not bool(image.save(str(path), "PNG")):
                return None
            entries = list(snapshot.entries)
            entries.append(
                MemoryAlbumEntry(
                    path=path,
                    captured_at=captured_at.isoformat(),
                    kind=str(kind or ""),
                    participants=tuple(
                        dict.fromkeys(
                            str(name or "").strip()
                            for name in (participants or ())
                            if str(name or "").strip()
                        )
                    ),
                )
            )
            self._write_entries(entries)
        except Exception as error:
            log_suppressed_exception("memory_album.save_capture", error)
            try:
                path.unlink(missing_ok=True)
            except Exception as cleanup_error:
                log_suppressed_exception(
                    "memory_album.cleanup_failed_capture",
                    cleanup_error,
                )
            return None
        return path

    def _available_timestamp_path(self, captured_at):
        for offset in range(1000):
            candidate_at = captured_at
            if offset:
                candidate_at = captured_at + timedelta(milliseconds=offset)
            filename = candidate_at.strftime("%Y%m%d-%H%M%S-") + f"{candidate_at.microsecond // 1000:03d}.png"
            path = self.root / filename
            if not path.exists():
                return path
        raise RuntimeError("memory album timestamp collision")

    def _load_entries(self):
        raw_by_name = {}
        try:
            raw = json.loads(self.index_path.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                raw_by_name = {
                    str(item.get("filename", "")): item
                    for item in raw
                    if isinstance(item, dict)
                }
        except (OSError, ValueError, TypeError) as error:
            if self.index_path.exists():
                log_suppressed_exception("memory_album.load_index", error)
        entries = []
        try:
            paths = sorted(self.root.glob("*.png"), reverse=True)
        except OSError as error:
            log_suppressed_exception("memory_album.list_photos", error)
            paths = []
        for path in paths:
            metadata = raw_by_name.get(path.name, {})
            entries.append(
                MemoryAlbumEntry(
                    path=path,
                    captured_at=str(metadata.get("captured_at", path.stem)),
                    kind=str(metadata.get("kind", "") or ""),
                    participants=tuple(metadata.get("participants", ()) or ()),
                )
            )
        return tuple(entries)

    def _write_entries(self, entries):
        payload = [
            {
                "filename": entry.path.name,
                "captured_at": entry.captured_at,
                "kind": entry.kind,
                "participants": list(entry.participants),
            }
            for entry in sorted(entries, key=lambda item: item.captured_at, reverse=True)
        ]
        self.index_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
