from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from uuid import uuid4

from .activity_rules import (
    ActivityBusyDecision,
    decide_activity_busy,
    decide_activity_interrupt,
    evaluate_activity_start,
    resolve_activity_policy,
)
from .activity_state import (
    ActiveActivity,
    ActivityDomainEvent,
    ActivityParticipant,
    ActivityParticipantSnapshot,
    ActivitySpec,
    ActivityStateProjection,
    PetActivityState,
)


@dataclass(frozen=True)
class ActivityStartResult:
    started: bool
    reason: str = ""
    participant_name: str = ""
    activity_id: str = ""
    events: tuple[ActivityDomainEvent, ...] = ()
    projections: tuple[ActivityStateProjection, ...] = ()


@dataclass(frozen=True)
class ActivityTransitionResult:
    handled: bool
    reason: str = ""
    activity_id: str = ""
    finished: bool = False
    result_committed: bool = False
    events: tuple[ActivityDomainEvent, ...] = ()
    projections: tuple[ActivityStateProjection, ...] = ()
    released_participant_names: tuple[str, ...] = ()


class ActivityCoordinator:
    def __init__(
        self,
        *,
        activity_id_factory: Callable[[], str] | None = None,
        event_id_factory: Callable[[], str] | None = None,
    ):
        self._activity_id_factory = activity_id_factory or (
            lambda: uuid4().hex
        )
        self._event_id_factory = event_id_factory or (
            lambda: uuid4().hex
        )
        self._activities: dict[str, ActiveActivity] = {}
        self._participant_activity_ids: dict[str, str] = {}

    def get_activity(self, activity_id: str) -> ActiveActivity | None:
        return self._activities.get(str(activity_id or ""))

    def get_activity_for_participant(
        self,
        participant_name: str,
    ) -> ActiveActivity | None:
        activity_id = self._participant_activity_ids.get(
            str(participant_name or "")
        )
        return self._activities.get(activity_id or "")

    def get_active_activities(self) -> tuple[ActiveActivity, ...]:
        return tuple(self._activities.values())

    def start(
        self,
        spec: ActivitySpec,
        *,
        owner_name: str,
        participant_snapshots: tuple[ActivityParticipantSnapshot, ...],
        now: float,
        source: str = "runtime",
        metadata: dict[str, object] | None = None,
    ) -> ActivityStartResult:
        snapshots = tuple(participant_snapshots or ())
        decision = evaluate_activity_start(
            spec,
            owner_name,
            snapshots,
        )
        if not decision.allowed:
            return ActivityStartResult(
                started=False,
                reason=decision.reason,
                participant_name=decision.participant_name,
            )

        for snapshot in snapshots:
            participant_name = snapshot.participant.name
            if participant_name in self._participant_activity_ids:
                return ActivityStartResult(
                    started=False,
                    reason="participant_owned",
                    participant_name=participant_name,
                )

        activity_id = str(self._activity_id_factory() or "").strip()
        if not activity_id:
            return ActivityStartResult(
                started=False,
                reason="empty_activity_id",
            )
        if activity_id in self._activities:
            return ActivityStartResult(
                started=False,
                reason="activity_id_collision",
                activity_id=activity_id,
            )

        now = float(now)
        participants = tuple(
            snapshot.participant
            for snapshot in snapshots
        )
        first_phase = spec.phases[0]
        activity = ActiveActivity(
            activity_id=activity_id,
            spec=spec,
            owner_name=str(owner_name),
            participants=participants,
            source=str(source or "runtime"),
            started_at=now,
            phase_index=0,
            phase_started_at=now,
            phase_ends_at=now + first_phase.duration_seconds,
            deadline_at=now + spec.duration_seconds,
            metadata=dict(metadata or {}),
        )
        self._activities[activity_id] = activity
        for participant in participants:
            self._participant_activity_ids[participant.name] = activity_id

        event = self._build_event(
            activity,
            "activity.started",
            occurred_at=now,
        )
        return ActivityStartResult(
            started=True,
            activity_id=activity_id,
            events=(event,),
            projections=self._build_projections(activity),
        )

    def update(
        self,
        activity_id: str,
        *,
        now: float,
    ) -> ActivityTransitionResult:
        activity = self.get_activity(activity_id)
        if activity is None:
            return ActivityTransitionResult(
                handled=False,
                reason="activity_not_found",
                activity_id=str(activity_id or ""),
            )

        now = float(now)
        events = []
        while now >= activity.phase_ends_at:
            transition_at = activity.phase_ends_at
            previous_phase = activity.phase.name
            next_phase_index = activity.phase_index + 1
            if next_phase_index >= len(activity.spec.phases):
                events.append(
                    self._build_event(
                        activity,
                        "activity.completed",
                        occurred_at=transition_at,
                    )
                )
                released_names = self._release_activity(activity)
                return ActivityTransitionResult(
                    handled=True,
                    activity_id=activity.activity_id,
                    finished=True,
                    result_committed=activity.result_committed,
                    events=tuple(events),
                    released_participant_names=released_names,
                )

            activity.phase_index = next_phase_index
            activity.phase_started_at = transition_at
            activity.phase_ends_at = (
                transition_at + activity.phase.duration_seconds
            )
            events.append(
                self._build_event(
                    activity,
                    "activity.phase_changed",
                    occurred_at=transition_at,
                    metadata={"previous_phase": previous_phase},
                )
            )

        return ActivityTransitionResult(
            handled=True,
            activity_id=activity.activity_id,
            result_committed=activity.result_committed,
            events=tuple(events),
            projections=self._build_projections(activity),
        )

    def finish(
        self,
        activity_id: str,
        *,
        now: float,
        reason: str = "manual_finish",
    ) -> ActivityTransitionResult:
        return self._terminate(
            activity_id,
            now=now,
            event_name="activity.completed",
            reason=reason,
        )

    def transition_to_phase(
        self,
        activity_id: str,
        *,
        phase_name: str,
        now: float,
        reason: str = "manual_transition",
    ) -> ActivityTransitionResult:
        activity = self.get_activity(activity_id)
        if activity is None:
            return ActivityTransitionResult(
                handled=False,
                reason="activity_not_found",
                activity_id=str(activity_id or ""),
            )
        phase_name = str(phase_name or "").strip()
        target_index = next(
            (
                index
                for index, phase in enumerate(activity.spec.phases)
                if phase.name == phase_name
            ),
            -1,
        )
        if target_index < 0:
            return ActivityTransitionResult(
                handled=False,
                reason="phase_not_found",
                activity_id=activity.activity_id,
                projections=self._build_projections(activity),
            )
        if target_index == activity.phase_index:
            return ActivityTransitionResult(
                handled=False,
                reason="already_in_phase",
                activity_id=activity.activity_id,
                projections=self._build_projections(activity),
            )
        if target_index < activity.phase_index:
            return ActivityTransitionResult(
                handled=False,
                reason="backward_phase_transition",
                activity_id=activity.activity_id,
                projections=self._build_projections(activity),
            )

        now = float(now)
        previous_phase = activity.phase.name
        activity.phase_index = target_index
        activity.phase_started_at = now
        activity.phase_ends_at = now + activity.phase.duration_seconds
        activity.deadline_at = now + sum(
            phase.duration_seconds
            for phase in activity.spec.phases[target_index:]
        )
        event = self._build_event(
            activity,
            "activity.phase_changed",
            occurred_at=now,
            reason=str(reason or ""),
            metadata={"previous_phase": previous_phase},
        )
        return ActivityTransitionResult(
            handled=True,
            activity_id=activity.activity_id,
            events=(event,),
            projections=self._build_projections(activity),
        )

    def cancel(
        self,
        activity_id: str,
        *,
        now: float,
        reason: str = "manual",
    ) -> ActivityTransitionResult:
        return self._terminate(
            activity_id,
            now=now,
            event_name="activity.cancelled",
            reason=reason,
        )

    def interrupt(
        self,
        activity_id: str,
        *,
        now: float,
        reason: str,
        force: bool = False,
    ) -> ActivityTransitionResult:
        activity = self.get_activity(activity_id)
        if activity is None:
            return ActivityTransitionResult(
                handled=False,
                reason="activity_not_found",
                activity_id=str(activity_id or ""),
            )
        decision = decide_activity_interrupt(activity, force=force)
        if not decision.allowed:
            return ActivityTransitionResult(
                handled=False,
                reason=decision.reason,
                activity_id=activity.activity_id,
                result_committed=activity.result_committed,
                projections=self._build_projections(activity),
            )
        return self._terminate(
            activity.activity_id,
            now=now,
            event_name="activity.interrupted",
            reason=reason,
        )

    def commit_result(
        self,
        activity_id: str,
        *,
        now: float,
        result: dict[str, object] | None = None,
    ) -> ActivityTransitionResult:
        activity = self.get_activity(activity_id)
        if activity is None:
            return ActivityTransitionResult(
                handled=False,
                reason="activity_not_found",
                activity_id=str(activity_id or ""),
            )
        if activity.result_committed:
            return ActivityTransitionResult(
                handled=False,
                reason="result_already_committed",
                activity_id=activity.activity_id,
                result_committed=True,
                projections=self._build_projections(activity),
            )

        activity.result_committed = True
        activity.committed_result = dict(result or {})
        event = self._build_event(
            activity,
            "activity.result_committed",
            occurred_at=float(now),
        )
        return ActivityTransitionResult(
            handled=True,
            activity_id=activity.activity_id,
            result_committed=True,
            events=(event,),
            projections=self._build_projections(activity),
        )

    def is_busy_for(
        self,
        participant_name: str,
        operation: str,
    ) -> ActivityBusyDecision:
        activity = self.get_activity_for_participant(participant_name)
        if activity is None:
            return ActivityBusyDecision(False)
        return decide_activity_busy(activity, operation)

    def _terminate(
        self,
        activity_id: str,
        *,
        now: float,
        event_name: str,
        reason: str,
    ) -> ActivityTransitionResult:
        activity = self.get_activity(activity_id)
        if activity is None:
            return ActivityTransitionResult(
                handled=False,
                reason="activity_not_found",
                activity_id=str(activity_id or ""),
            )
        event = self._build_event(
            activity,
            event_name,
            occurred_at=float(now),
            reason=str(reason or ""),
        )
        released_names = self._release_activity(activity)
        return ActivityTransitionResult(
            handled=True,
            activity_id=activity.activity_id,
            finished=True,
            result_committed=activity.result_committed,
            events=(event,),
            released_participant_names=released_names,
        )

    def _release_activity(
        self,
        activity: ActiveActivity,
    ) -> tuple[str, ...]:
        released_names = tuple(
            participant.name
            for participant in activity.participants
        )
        self._activities.pop(activity.activity_id, None)
        for participant_name in released_names:
            if (
                self._participant_activity_ids.get(participant_name)
                == activity.activity_id
            ):
                self._participant_activity_ids.pop(participant_name, None)
        return released_names

    def _build_projections(
        self,
        activity: ActiveActivity,
    ) -> tuple[ActivityStateProjection, ...]:
        policy = resolve_activity_policy(
            activity.spec,
            activity.phase_index,
        )
        return tuple(
            ActivityStateProjection(
                participant_name=participant.name,
                state=PetActivityState(
                    activity_id=activity.activity_id,
                    activity_kind=activity.spec.kind,
                    owner_name=activity.owner_name,
                    participant_role=participant.role,
                    phase=activity.phase.name,
                    started_at=activity.started_at,
                    phase_started_at=activity.phase_started_at,
                    phase_ends_at=activity.phase_ends_at,
                    deadline_at=activity.deadline_at,
                    blocked_operations=policy.blocked_operations,
                    collision_policy=policy.collision_policy,
                    interrupt_policy=policy.interrupt_policy,
                ),
            )
            for participant in activity.participants
        )

    def _build_event(
        self,
        activity: ActiveActivity,
        event_name: str,
        *,
        occurred_at: float,
        reason: str = "",
        metadata: dict[str, object] | None = None,
    ) -> ActivityDomainEvent:
        event_metadata = dict(activity.metadata)
        event_metadata.update(metadata or {})
        return ActivityDomainEvent(
            event_name=event_name,
            event_id=str(self._event_id_factory() or ""),
            activity_id=activity.activity_id,
            activity_kind=activity.spec.kind,
            owner_name=activity.owner_name,
            participants=activity.participants,
            phase=activity.phase.name,
            occurred_at=float(occurred_at),
            started_at=activity.started_at,
            source=activity.source,
            reason=reason,
            result=dict(activity.committed_result),
            metadata=event_metadata,
        )
