from __future__ import annotations

from collections.abc import Callable, Mapping

from .achievement_catalog import AchievementCatalog
from .achievement_eligibility import (
    AchievementEligibilityDecision,
    AchievementEligibilityGuard,
    INELIGIBLE_MISSING_SESSION,
    classify_achievement_source_kind,
)
from .achievement_state import AchievementState
from .achievement_tracker import (
    AchievementConsumeResult,
    AchievementGameplayEvent,
    AchievementTracker,
)


class AchievementRuntimeService:
    """Connects Runtime lifecycle boundaries to the pure achievement tracker."""

    def __init__(
        self,
        *,
        catalog: AchievementCatalog,
        state: AchievementState,
        eligibility_guard: AchievementEligibilityGuard,
        time_scale_provider: Callable[[], float],
        state_changed_callback: Callable[[AchievementConsumeResult], object]
        | None = None,
    ):
        self.catalog = catalog
        self.state = state
        self.eligibility_guard = eligibility_guard
        self.time_scale_provider = time_scale_provider
        self.state_changed_callback = state_changed_callback
        self.tracker = AchievementTracker(catalog, state)
        self.last_consume_result = AchievementConsumeResult(
            False,
            "not_started",
        )

    def begin_activity_session(
        self,
        *,
        activity_id: str,
        world_mode: str,
        source: str,
        execution_mode: str,
        started_at: float,
    ) -> bool:
        activity_id = str(activity_id or "").strip()
        if not activity_id:
            return False
        if activity_id in self.eligibility_guard.active_session_ids:
            return False
        source_kind = classify_achievement_source_kind(
            source,
            execution_mode,
        )
        self.eligibility_guard.begin_session(
            session_id=activity_id,
            world_mode=world_mode,
            source_kind=source_kind,
            time_scale=self._time_scale(),
            started_at=started_at,
        )
        return True

    def cancel_activity_session(
        self,
        activity_id: str,
        *,
        reason: str,
    ) -> bool:
        return self.eligibility_guard.cancel_session(
            activity_id,
            reason=reason,
        )

    def cancel_all_activity_sessions(self, *, reason: str) -> tuple[str, ...]:
        cancelled = []
        for activity_id in tuple(
            self.eligibility_guard.active_session_ids
        ):
            if self.cancel_activity_session(activity_id, reason=reason):
                cancelled.append(activity_id)
        return tuple(cancelled)

    def consume_activity_metadata(
        self,
        metadata,
    ) -> AchievementConsumeResult:
        if not isinstance(metadata, Mapping):
            return AchievementConsumeResult(False, "missing_activity_metadata")
        event_name = str(
            metadata.get("activity_event_name", "") or ""
        ).strip()
        if not event_name:
            return AchievementConsumeResult(False, "not_activity_event_metadata")

        event_id = str(
            metadata.get("activity_event_id", "") or ""
        ).strip()
        activity_id = str(metadata.get("activity_id", "") or "").strip()
        world_mode = str(
            metadata.get(
                "activity_world_mode",
                metadata.get("world_mode", ""),
            )
            or ""
        ).strip()
        source = str(metadata.get("activity_source", "") or "")
        execution_mode = str(
            metadata.get("activity_execution_mode", "") or ""
        )
        ended_at = _safe_float(
            metadata.get("activity_ended_at"),
            0.0,
        )

        if activity_id in self.eligibility_guard.active_session_ids:
            decision = self.eligibility_guard.finish_session(
                session_id=activity_id,
                event_id=event_id,
                world_mode=world_mode,
                time_scale=self._time_scale(),
                ended_at=ended_at,
            )
        else:
            decision = AchievementEligibilityDecision(
                eligible=False,
                reason=INELIGIBLE_MISSING_SESSION,
                event_id=event_id,
                session_id=activity_id,
                world_mode=world_mode,
                source_kind=classify_achievement_source_kind(
                    source,
                    execution_mode,
                ),
                started_at=_safe_float(
                    metadata.get("activity_started_at"),
                    0.0,
                ),
                ended_at=ended_at,
            )

        event = AchievementGameplayEvent.from_eligibility_decision(
            decision,
            event_name=event_name,
            payload=dict(metadata),
            participants=metadata.get("activity_participants", ()),
        )
        result = self.tracker.consume_event(event)
        self.last_consume_result = result
        if result.accepted and callable(self.state_changed_callback):
            self.state_changed_callback(result)
        return result

    def consume_instantaneous_activity_metadata(
        self,
        metadata,
    ) -> AchievementConsumeResult:
        if not isinstance(metadata, Mapping):
            return AchievementConsumeResult(False, "missing_activity_metadata")
        event_name = str(
            metadata.get("activity_event_name", "") or ""
        ).strip()
        if not event_name:
            return AchievementConsumeResult(False, "not_activity_event_metadata")
        event_id = str(
            metadata.get("activity_event_id", "") or ""
        ).strip()
        world_mode = str(
            metadata.get(
                "activity_world_mode",
                metadata.get("world_mode", ""),
            )
            or ""
        ).strip()
        source_kind = classify_achievement_source_kind(
            str(metadata.get("activity_source", "") or ""),
            str(metadata.get("activity_execution_mode", "") or ""),
        )
        occurred_at = _safe_float(
            metadata.get("activity_ended_at"),
            0.0,
        )
        decision = self.eligibility_guard.qualify_instantaneous(
            event_id=event_id,
            world_mode=world_mode,
            source_kind=source_kind,
            time_scale=self._time_scale(),
            occurred_at=occurred_at,
        )
        event = AchievementGameplayEvent.from_eligibility_decision(
            decision,
            event_name=event_name,
            payload=dict(metadata),
            participants=metadata.get("activity_participants", ()),
        )
        return self._store_consume_result(self.tracker.consume_event(event))

    def consume_state_snapshot(
        self,
        *,
        snapshot_id: str,
        world_mode: str,
        source: str,
        execution_mode: str,
        occurred_at: float,
        state_payload: Mapping[str, object],
        eligible: bool = True,
        ineligible_reason: str = "",
    ) -> AchievementConsumeResult:
        source_kind = classify_achievement_source_kind(
            source,
            execution_mode,
        )
        time_scale_eligible = self._time_scale() == 1.0
        result = self.tracker.consume_state_snapshot(
            snapshot_id=str(snapshot_id or ""),
            world_mode=str(world_mode or ""),
            source_kind=source_kind,
            occurred_at=float(occurred_at),
            state_payload=dict(state_payload or {}),
            eligible=bool(eligible and time_scale_eligible),
            ineligible_reason=(
                str(ineligible_reason or "")
                if eligible
                else str(ineligible_reason or "ineligible_state_snapshot")
            )
            or (
                "time_scale_not_1x_at_snapshot"
                if not time_scale_eligible
                else ""
            ),
        )
        return self._store_consume_result(result)

    def activity_session_is_eligible(
        self,
        activity_id: str,
        *,
        world_mode: str,
    ) -> bool:
        return self.eligibility_guard.session_is_eligible(
            activity_id,
            world_mode=world_mode,
        )

    def _store_consume_result(
        self,
        result: AchievementConsumeResult,
    ) -> AchievementConsumeResult:
        self.last_consume_result = result
        if result.accepted and callable(self.state_changed_callback):
            self.state_changed_callback(result)
        return result

    def _time_scale(self) -> float:
        try:
            return float(self.time_scale_provider())
        except (TypeError, ValueError):
            return 1.0


def _safe_float(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)
