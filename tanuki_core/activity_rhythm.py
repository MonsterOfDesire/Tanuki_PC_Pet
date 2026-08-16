from dataclasses import dataclass

from .ui_localization import translate_ui


@dataclass(frozen=True)
class CharacterRhythmSnapshot:
    character_name: str
    summoned: bool
    sleep_status: str = "unscheduled"
    sleepiness_percent: float | None = None
    transformation_status: str = "unavailable"
    transformation_remaining_seconds: float | None = None


@dataclass(frozen=True)
class ActivityRhythmSnapshot:
    observed_at: float
    race_status: str = "unscheduled"
    race_remaining_seconds: float | None = None
    race_wait_reason: str = ""
    chorus_status: str = "unscheduled"
    chorus_remaining_seconds: float | None = None
    chorus_wait_reason: str = ""
    members: tuple[CharacterRhythmSnapshot, ...] = ()


def clamp_percent(value) -> float:
    return max(0.0, min(100.0, float(value)))


def format_compact_duration(seconds) -> str:
    try:
        value = max(0, int(round(float(seconds))))
    except (TypeError, ValueError):
        return ""
    minutes, remaining = divmod(value, 60)
    if minutes:
        return translate_ui(
            "common.duration_minutes_seconds",
            default="{minutes}分{seconds:02d}秒",
            minutes=minutes,
            seconds=remaining,
        )
    return translate_ui(
        "common.duration_seconds",
        default="{seconds}秒",
        seconds=remaining,
    )
