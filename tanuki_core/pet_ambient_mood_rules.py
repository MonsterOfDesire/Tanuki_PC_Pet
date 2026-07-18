from dataclasses import dataclass


SOLITUDE_EVENT_THRESHOLD_SECONDS = 40.0
SOLITUDE_EVENT_COOLDOWN_SECONDS = 48.0
CROWDING_EVENT_COOLDOWN_SECONDS = 18.0
OFFER_MISS_MIN_HOVER_SECONDS = 1.2
OFFER_MISS_COOLDOWN_SECONDS = 12.0
COMMON_NEGATIVE_FORBIDDEN_MOODS = (
    "happy",
    "smile",
    "relief",
    "calm",
    "confidence",
    "cool",
    "glance",
)


@dataclass(frozen=True)
class AmbientMoodEventDecision:
    should_trigger: bool
    event_kind: str = ""
    mood_delta: float = 0.0
    preferred_moods: tuple[str, ...] = ()
    forbidden_moods: tuple[str, ...] = COMMON_NEGATIVE_FORBIDDEN_MOODS
    afterglow_duration: float = 0.0
    cooldown_seconds: float = 0.0
    reason: str = ""


def _no_event(reason):
    return AmbientMoodEventDecision(should_trigger=False, reason=reason)


def resolve_solitude_event(*, is_adult, now, last_company_seen_at, visible_pet_count, cooldown_until, mood_score):
    if visible_pet_count > 0:
        return _no_event("not_alone")
    if float(now) < float(cooldown_until):
        return _no_event("cooldown")
    if float(mood_score) < 15.0:
        return _no_event("already_low")
    if float(last_company_seen_at) <= 0.0:
        return _no_event("unseeded")
    if (float(now) - float(last_company_seen_at)) < SOLITUDE_EVENT_THRESHOLD_SECONDS:
        return _no_event("not_alone_long_enough")
    return AmbientMoodEventDecision(
        should_trigger=True,
        event_kind="solitude",
        mood_delta=3.0 if is_adult else 5.0,
        preferred_moods=("sad", "think"),
        afterglow_duration=3.5,
        cooldown_seconds=SOLITUDE_EVENT_COOLDOWN_SECONDS,
        reason="long_solitude",
    )


def resolve_crowding_event(*, is_adult, now, cooldown_until, collision_delta_x, is_busy):
    if is_busy:
        return _no_event("busy")
    if float(now) < float(cooldown_until):
        return _no_event("cooldown")
    if int(collision_delta_x) == 0:
        return _no_event("no_displacement")
    return AmbientMoodEventDecision(
        should_trigger=True,
        event_kind="crowding",
        mood_delta=2.0 if is_adult else 3.0,
        preferred_moods=("angry", "sad", "think"),
        afterglow_duration=2.5,
        cooldown_seconds=CROWDING_EVENT_COOLDOWN_SECONDS,
        reason="crowded_displacement",
    )


def resolve_offer_miss_event(*, now, hover_started_at, hover_timeout_seconds, cooldown_until):
    if float(now) < float(cooldown_until):
        return _no_event("cooldown")
    if float(hover_started_at) <= 0.0:
        return _no_event("unseeded")
    elapsed = float(now) - float(hover_started_at)
    if elapsed < OFFER_MISS_MIN_HOVER_SECONDS:
        return _no_event("hover_too_short")
    if elapsed >= float(hover_timeout_seconds):
        return _no_event("handled_by_timeout_scene")
    return AmbientMoodEventDecision(
        should_trigger=True,
        event_kind="offer_miss",
        mood_delta=4.0,
        preferred_moods=("sad", "think"),
        afterglow_duration=3.0,
        cooldown_seconds=OFFER_MISS_COOLDOWN_SECONDS,
        reason="offer_missed",
    )
