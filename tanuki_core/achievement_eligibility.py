from __future__ import annotations

from dataclasses import dataclass

from .achievement_catalog import ACHIEVEMENT_WORLD_MODES


ACHIEVEMENT_SOURCE_AUTONOMOUS = "autonomous_gameplay"
ACHIEVEMENT_SOURCE_PLAYER = "player_gameplay"
ACHIEVEMENT_SOURCE_SETTINGS_PREVIEW = "settings_preview"
ACHIEVEMENT_SOURCE_SETTINGS_TEST = "settings_test_control"
ACHIEVEMENT_SOURCE_DEBUG = "debug"
ACHIEVEMENT_SOURCE_TEST = "test"

ACHIEVEMENT_ELIGIBLE_SOURCE_KINDS = frozenset(
    {
        ACHIEVEMENT_SOURCE_AUTONOMOUS,
        ACHIEVEMENT_SOURCE_PLAYER,
    }
)
ACHIEVEMENT_EXCLUDED_SOURCE_KINDS = frozenset(
    {
        ACHIEVEMENT_SOURCE_SETTINGS_PREVIEW,
        ACHIEVEMENT_SOURCE_SETTINGS_TEST,
        ACHIEVEMENT_SOURCE_DEBUG,
        ACHIEVEMENT_SOURCE_TEST,
    }
)

INELIGIBLE_TIME_SCALE_AT_START = "time_scale_not_1x_at_start"
INELIGIBLE_TIME_SCALE_CHANGED = "time_scale_changed_during_session"
INELIGIBLE_WORLD_MODE_CHANGED = "world_mode_changed_during_session"
INELIGIBLE_TEST_SOURCE = "test_source"
INELIGIBLE_UNKNOWN_SOURCE = "unknown_source_kind"
INELIGIBLE_MISSING_EVENT_ID = "missing_event_id"
INELIGIBLE_MISSING_SESSION = "missing_eligibility_session"


@dataclass
class AchievementEligibilityToken:
    session_id: str
    world_mode: str
    source_kind: str
    started_at: float
    started_time_scale: float
    eligible: bool = True
    ineligible_reason: str = ""

    def invalidate(self, reason: str) -> bool:
        if not self.eligible:
            return False
        self.eligible = False
        self.ineligible_reason = str(reason or "").strip()
        return True


@dataclass(frozen=True)
class AchievementEligibilityDecision:
    eligible: bool
    reason: str
    event_id: str
    session_id: str
    world_mode: str
    source_kind: str
    started_at: float
    ended_at: float


class AchievementEligibilityGuard:
    def __init__(self):
        self._active_tokens: dict[str, AchievementEligibilityToken] = {}

    @property
    def active_session_ids(self) -> frozenset[str]:
        return frozenset(self._active_tokens)

    def session_is_eligible(
        self,
        session_id: str,
        *,
        world_mode: str | None = None,
    ) -> bool:
        token = self._active_tokens.get(str(session_id or "").strip())
        if token is None or not token.eligible:
            return False
        if world_mode is None:
            return True
        return token.world_mode == str(world_mode or "").strip()

    def begin_session(
        self,
        *,
        session_id: str,
        world_mode: str,
        source_kind: str,
        time_scale: float,
        started_at: float,
    ) -> AchievementEligibilityToken:
        session_id = str(session_id or "").strip()
        if not session_id:
            raise ValueError("achievement eligibility session_id is required")
        if session_id in self._active_tokens:
            raise ValueError(f"achievement eligibility session already exists: {session_id}")

        world_mode = _normalize_world_mode(world_mode)
        source_kind = str(source_kind or "").strip()
        token = AchievementEligibilityToken(
            session_id=session_id,
            world_mode=world_mode,
            source_kind=source_kind,
            started_at=float(started_at),
            started_time_scale=float(time_scale),
        )
        reason = _initial_ineligible_reason(
            source_kind=source_kind,
            time_scale=time_scale,
        )
        if reason:
            token.invalidate(reason)
        self._active_tokens[session_id] = token
        return token

    def observe_time_scale(self, time_scale: float) -> tuple[str, ...]:
        if _is_one_x(time_scale):
            return ()
        invalidated = []
        for session_id, token in self._active_tokens.items():
            if token.invalidate(INELIGIBLE_TIME_SCALE_CHANGED):
                invalidated.append(session_id)
        return tuple(invalidated)

    def observe_world_mode(self, world_mode: str) -> tuple[str, ...]:
        world_mode = _normalize_world_mode(world_mode)
        invalidated = []
        for session_id, token in self._active_tokens.items():
            if (
                token.world_mode != world_mode
                and token.invalidate(INELIGIBLE_WORLD_MODE_CHANGED)
            ):
                invalidated.append(session_id)
        return tuple(invalidated)

    def invalidate_session(self, session_id: str, reason: str) -> bool:
        token = self._active_tokens.get(str(session_id or "").strip())
        return bool(token and token.invalidate(reason))

    def cancel_session(self, session_id: str, *, reason: str) -> bool:
        token = self._active_tokens.pop(
            str(session_id or "").strip(),
            None,
        )
        if token is None:
            return False
        token.invalidate(str(reason or "activity_cancelled"))
        return True

    def finish_session(
        self,
        *,
        session_id: str,
        event_id: str,
        world_mode: str,
        time_scale: float,
        ended_at: float,
    ) -> AchievementEligibilityDecision:
        session_id = str(session_id or "").strip()
        event_id = str(event_id or "").strip()
        token = self._active_tokens.pop(session_id, None)
        if token is None:
            return AchievementEligibilityDecision(
                eligible=False,
                reason=INELIGIBLE_MISSING_SESSION,
                event_id=event_id,
                session_id=session_id,
                world_mode=str(world_mode or "").strip(),
                source_kind="",
                started_at=0.0,
                ended_at=float(ended_at),
            )

        normalized_world_mode = _normalize_world_mode(world_mode)
        if token.world_mode != normalized_world_mode:
            token.invalidate(INELIGIBLE_WORLD_MODE_CHANGED)
        if not _is_one_x(time_scale):
            token.invalidate(INELIGIBLE_TIME_SCALE_CHANGED)
        if not event_id:
            token.invalidate(INELIGIBLE_MISSING_EVENT_ID)

        return AchievementEligibilityDecision(
            eligible=bool(token.eligible),
            reason=str(token.ineligible_reason or ""),
            event_id=event_id,
            session_id=token.session_id,
            world_mode=token.world_mode,
            source_kind=token.source_kind,
            started_at=float(token.started_at),
            ended_at=float(ended_at),
        )

    def qualify_instantaneous(
        self,
        *,
        event_id: str,
        world_mode: str,
        source_kind: str,
        time_scale: float,
        occurred_at: float,
    ) -> AchievementEligibilityDecision:
        event_id = str(event_id or "").strip()
        world_mode = _normalize_world_mode(world_mode)
        source_kind = str(source_kind or "").strip()
        reason = _initial_ineligible_reason(
            source_kind=source_kind,
            time_scale=time_scale,
        )
        if not event_id:
            reason = INELIGIBLE_MISSING_EVENT_ID
        return AchievementEligibilityDecision(
            eligible=not bool(reason),
            reason=reason,
            event_id=event_id,
            session_id="",
            world_mode=world_mode,
            source_kind=source_kind,
            started_at=float(occurred_at),
            ended_at=float(occurred_at),
        )


def classify_achievement_source_kind(
    source: str,
    execution_mode: str = "",
) -> str:
    source = str(source or "").strip().lower()
    execution_mode = str(execution_mode or "").strip().lower()
    combined = f"{source} {execution_mode}"
    if "settings_preview" in combined or "preview" in execution_mode:
        return ACHIEVEMENT_SOURCE_SETTINGS_PREVIEW
    if "settings_test" in combined or "test_control" in combined:
        return ACHIEVEMENT_SOURCE_SETTINGS_TEST
    if "debug" in combined:
        return ACHIEVEMENT_SOURCE_DEBUG
    if execution_mode == "test" or source == "test":
        return ACHIEVEMENT_SOURCE_TEST
    if "player" in combined or "manual_gameplay" in combined:
        return ACHIEVEMENT_SOURCE_PLAYER
    if source or execution_mode in {"autonomous", "normal"}:
        return ACHIEVEMENT_SOURCE_AUTONOMOUS
    return ""


def _initial_ineligible_reason(*, source_kind: str, time_scale: float) -> str:
    if source_kind in ACHIEVEMENT_EXCLUDED_SOURCE_KINDS:
        return INELIGIBLE_TEST_SOURCE
    if source_kind not in ACHIEVEMENT_ELIGIBLE_SOURCE_KINDS:
        return INELIGIBLE_UNKNOWN_SOURCE
    if not _is_one_x(time_scale):
        return INELIGIBLE_TIME_SCALE_AT_START
    return ""


def _is_one_x(time_scale: float) -> bool:
    try:
        return float(time_scale) == 1.0
    except (TypeError, ValueError):
        return False


def _normalize_world_mode(world_mode: str) -> str:
    world_mode = str(world_mode or "").strip()
    if world_mode not in ACHIEVEMENT_WORLD_MODES:
        raise ValueError(f"unsupported achievement world mode: {world_mode!r}")
    return world_mode
