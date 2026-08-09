from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .activity_event_contract import (
    ACTIVITY_EVENT_WORK_COMPLETED,
    build_activity_event_metadata,
)
from .activity_state import ActivityDomainEvent
from .household_event_rules import HouseholdResolvedEvent
from .rudolf_work_rules import (
    RUDOLF_NAME,
    RUDOLF_WORK_ACTIVITY_KIND,
    RUDOLF_WORK_INCOME,
    RUDOLF_WORK_MOOD_DELTA,
    RUDOLF_WORK_PRESSURE_RELIEF,
    RUDOLF_WORK_SETTLEMENT_KEY,
)


@dataclass(frozen=True)
class RudolfWorkSettlementDecision:
    ready: bool
    reason: str = ""
    household_event: HouseholdResolvedEvent | None = None


@dataclass(frozen=True)
class RudolfWorkSettlementApplyResult:
    applied: bool
    reason: str = ""
    household_event: HouseholdResolvedEvent | None = None
    recorded_entry: object | None = None


class RudolfWorkSettlementAdapter:
    def __init__(self):
        self._settled_activity_ids: set[str] = set()
        self._mood_applied_activity_ids: set[str] = set()

    @property
    def settled_activity_ids(self) -> frozenset[str]:
        return frozenset(self._settled_activity_ids)

    def resolve(
        self,
        event: ActivityDomainEvent | None,
    ) -> RudolfWorkSettlementDecision:
        if event is None:
            return RudolfWorkSettlementDecision(False, "missing_event")
        if event.event_name != "activity.result_committed":
            return RudolfWorkSettlementDecision(
                False,
                "unsupported_event",
            )
        if event.activity_kind != RUDOLF_WORK_ACTIVITY_KIND:
            return RudolfWorkSettlementDecision(
                False,
                "unsupported_activity",
            )
        activity_id = str(event.activity_id or "").strip()
        if not activity_id:
            return RudolfWorkSettlementDecision(
                False,
                "missing_activity_id",
            )
        if activity_id in self._settled_activity_ids:
            return RudolfWorkSettlementDecision(
                False,
                "activity_already_settled",
            )

        result = dict(event.result or {})
        if result.get("settlement_key") != RUDOLF_WORK_SETTLEMENT_KEY:
            return RudolfWorkSettlementDecision(
                False,
                "invalid_settlement_key",
            )
        if result.get("outcome") != "completed":
            return RudolfWorkSettlementDecision(
                False,
                "work_not_completed",
            )
        try:
            living_fund_delta = int(result.get("living_fund_delta"))
            household_pressure_delta = float(
                result.get("household_pressure_delta")
            )
            mood_delta = float(result.get("mood_delta"))
        except (TypeError, ValueError):
            return RudolfWorkSettlementDecision(
                False,
                "invalid_result_delta",
            )
        if (
            living_fund_delta != RUDOLF_WORK_INCOME
            or household_pressure_delta != RUDOLF_WORK_PRESSURE_RELIEF
            or mood_delta != RUDOLF_WORK_MOOD_DELTA
        ):
            return RudolfWorkSettlementDecision(
                False,
                "unexpected_result_delta",
            )

        participant_roles = {
            participant.name: participant.role
            for participant in event.participants
        }
        metadata = build_activity_event_metadata(
            event_name=ACTIVITY_EVENT_WORK_COMPLETED,
            event_id=event.event_id,
            activity_id=activity_id,
            activity_kind=event.activity_kind,
            participants=participant_roles,
            source="activity_coordinator",
            execution_mode=str(
                event.metadata.get("execution_mode", "normal")
            ),
            world_mode=str(
                event.metadata.get("start_world_mode", "golden_legend")
            ),
            phase=event.phase,
            started_at=event.started_at,
            ended_at=event.occurred_at,
            outcome=result["outcome"],
            extra={
                "source": "activity_coordinator",
                "activity_schema_version": event.schema_version,
                "participant_roles": participant_roles,
                "settlement_key": RUDOLF_WORK_SETTLEMENT_KEY,
                "outcome": result["outcome"],
                "completion_ratio": float(
                    result.get("completion_ratio", 1.0)
                ),
            },
        )
        household_event = HouseholdResolvedEvent(
            occurred_at=float(event.occurred_at),
            category="economy",
            event_type="rudolf_work_completed",
            channel="economy",
            importance="normal",
            summary="魯道夫完成工作，替家裡賺了一筆生活費。",
            actor_name=RUDOLF_NAME,
            mood_delta=mood_delta,
            tags=("activity", "work", "completed"),
            living_fund_delta=living_fund_delta,
            household_pressure_delta=household_pressure_delta,
            metadata=metadata,
        )
        return RudolfWorkSettlementDecision(
            True,
            household_event=household_event,
        )

    def apply(
        self,
        event: ActivityDomainEvent | None,
        *,
        record_event: Callable[[HouseholdResolvedEvent], object],
        apply_mood_delta: Callable[[float], bool],
    ) -> RudolfWorkSettlementApplyResult:
        decision = self.resolve(event)
        if not decision.ready or decision.household_event is None:
            return RudolfWorkSettlementApplyResult(
                False,
                reason=decision.reason,
            )

        activity_id = event.activity_id
        if activity_id not in self._mood_applied_activity_ids:
            if not bool(
                apply_mood_delta(
                    float(decision.household_event.mood_delta)
                )
            ):
                return RudolfWorkSettlementApplyResult(
                    False,
                    reason="mood_apply_failed",
                    household_event=decision.household_event,
                )
            self._mood_applied_activity_ids.add(activity_id)

        recorded_entry = record_event(decision.household_event)
        if recorded_entry is None:
            return RudolfWorkSettlementApplyResult(
                False,
                reason="record_event_failed",
                household_event=decision.household_event,
            )

        self._settled_activity_ids.add(activity_id)
        return RudolfWorkSettlementApplyResult(
            True,
            household_event=decision.household_event,
            recorded_entry=recorded_entry,
        )
