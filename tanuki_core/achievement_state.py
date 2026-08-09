from __future__ import annotations

from dataclasses import dataclass, field

from .achievement_catalog import ACHIEVEMENT_WORLD_MODES


ACHIEVEMENT_PERSISTENCE_SCHEMA_VERSION = 1


@dataclass
class AchievementProgress:
    count: int = 0
    observed_keys: set[str] = field(default_factory=set)
    observed_event_names: set[str] = field(default_factory=set)
    unlocked_at: float | None = None
    completion_count: int = 0
    updated_at: float = 0.0

    @property
    def unlocked(self) -> bool:
        return self.unlocked_at is not None

    def unlock(self, occurred_at: float) -> bool:
        if self.unlocked:
            return False
        self.unlocked_at = float(occurred_at)
        self.updated_at = float(occurred_at)
        self.completion_count = max(1, int(self.completion_count) + 1)
        return True


@dataclass
class AchievementState:
    progress_by_world_mode: dict[
        str,
        dict[str, AchievementProgress],
    ] = field(
        default_factory=lambda: {
            mode: {} for mode in sorted(ACHIEVEMENT_WORLD_MODES)
        }
    )
    processed_event_ids: dict[str, set[str]] = field(
        default_factory=lambda: {
            mode: set() for mode in sorted(ACHIEVEMENT_WORLD_MODES)
        }
    )

    def progress_for(
        self,
        world_mode: str,
        achievement_id: str,
    ) -> AchievementProgress:
        world_mode = _require_world_mode(world_mode)
        achievement_id = str(achievement_id or "").strip()
        if not achievement_id:
            raise ValueError("achievement_id is required")
        progress_by_id = self.progress_by_world_mode.setdefault(
            world_mode,
            {},
        )
        return progress_by_id.setdefault(
            achievement_id,
            AchievementProgress(),
        )

    def is_unlocked(self, world_mode: str, achievement_id: str) -> bool:
        world_mode = _require_world_mode(world_mode)
        progress = self.progress_by_world_mode.get(world_mode, {}).get(
            str(achievement_id or "").strip()
        )
        return bool(progress and progress.unlocked)

    def has_processed_event(self, world_mode: str, event_id: str) -> bool:
        world_mode = _require_world_mode(world_mode)
        return str(event_id or "").strip() in self.processed_event_ids.setdefault(
            world_mode,
            set(),
        )

    def mark_event_processed(self, world_mode: str, event_id: str) -> None:
        world_mode = _require_world_mode(world_mode)
        event_id = str(event_id or "").strip()
        if not event_id:
            raise ValueError("event_id is required")
        self.processed_event_ids.setdefault(world_mode, set()).add(event_id)

    def clear(self) -> None:
        self.progress_by_world_mode = {
            mode: {} for mode in sorted(ACHIEVEMENT_WORLD_MODES)
        }
        self.processed_event_ids = {
            mode: set() for mode in sorted(ACHIEVEMENT_WORLD_MODES)
        }


def capture_achievement_persistence_state(
    state: AchievementState,
) -> dict[str, object]:
    return {
        "achievement_schema_version": (
            ACHIEVEMENT_PERSISTENCE_SCHEMA_VERSION
        ),
        "progress_by_world_mode": {
            world_mode: {
                achievement_id: _progress_to_payload(progress)
                for achievement_id, progress in sorted(
                    state.progress_by_world_mode.get(world_mode, {}).items()
                )
            }
            for world_mode in sorted(ACHIEVEMENT_WORLD_MODES)
        },
        "processed_event_ids": {
            world_mode: sorted(
                state.processed_event_ids.get(world_mode, set())
            )
            for world_mode in sorted(ACHIEVEMENT_WORLD_MODES)
        },
    }


def apply_achievement_persistence_state(
    payload,
    state: AchievementState,
) -> bool:
    if not isinstance(payload, dict):
        return False

    state.clear()
    raw_progress_by_mode = payload.get("progress_by_world_mode", {})
    if isinstance(raw_progress_by_mode, dict):
        for world_mode in ACHIEVEMENT_WORLD_MODES:
            raw_progress_by_id = raw_progress_by_mode.get(
                world_mode,
                {},
            )
            if not isinstance(raw_progress_by_id, dict):
                continue
            for achievement_id, raw_progress in raw_progress_by_id.items():
                achievement_id = str(achievement_id or "").strip()
                if not achievement_id or not isinstance(raw_progress, dict):
                    continue
                state.progress_by_world_mode[world_mode][achievement_id] = (
                    _progress_from_payload(raw_progress)
                )

    raw_processed_by_mode = payload.get("processed_event_ids", {})
    if isinstance(raw_processed_by_mode, dict):
        for world_mode in ACHIEVEMENT_WORLD_MODES:
            raw_event_ids = raw_processed_by_mode.get(world_mode, ())
            if not isinstance(raw_event_ids, list):
                continue
            state.processed_event_ids[world_mode].update(
                event_id
                for event_id in (
                    str(raw_event_id or "").strip()
                    for raw_event_id in raw_event_ids
                )
                if event_id
            )
    return True


def _progress_to_payload(progress: AchievementProgress) -> dict[str, object]:
    return {
        "count": max(0, int(progress.count)),
        "observed_keys": sorted(progress.observed_keys),
        "observed_event_names": sorted(progress.observed_event_names),
        "unlocked_at": (
            float(progress.unlocked_at)
            if progress.unlocked_at is not None
            else None
        ),
        "completion_count": max(0, int(progress.completion_count)),
        "updated_at": float(progress.updated_at),
    }


def _progress_from_payload(payload) -> AchievementProgress:
    unlocked_at = _safe_optional_float(payload.get("unlocked_at"))
    completion_count = max(
        0,
        _safe_int(payload.get("completion_count"), 0),
    )
    if unlocked_at is not None:
        completion_count = max(1, completion_count)
    return AchievementProgress(
        count=max(0, _safe_int(payload.get("count"), 0)),
        observed_keys=_safe_string_set(payload.get("observed_keys", ())),
        observed_event_names=_safe_string_set(
            payload.get("observed_event_names", ())
        ),
        unlocked_at=unlocked_at,
        completion_count=completion_count,
        updated_at=max(0.0, _safe_float(payload.get("updated_at"), 0.0)),
    )


def _safe_string_set(value) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {
        normalized
        for normalized in (
            str(item or "").strip() for item in value
        )
        if normalized
    }


def _safe_int(value, default=0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _safe_float(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _safe_optional_float(value) -> float | None:
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return None


def _require_world_mode(world_mode: str) -> str:
    world_mode = str(world_mode or "").strip()
    if world_mode not in ACHIEVEMENT_WORLD_MODES:
        raise ValueError(f"unsupported achievement world mode: {world_mode!r}")
    return world_mode
