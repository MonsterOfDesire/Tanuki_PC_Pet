from __future__ import annotations

from dataclasses import dataclass

from .activity_coordinator import ActivityCoordinator
from .activity_runtime_adapter import ActivityRuntimeAdapter
from .household_event_rules import (
    HouseholdEventScheduleState,
    RUDOLF_WORK_INTERVAL_SECONDS,
    consume_rudolf_work_schedule_if_due,
)
from .household_state import HouseholdState
from .rudolf_work_rules import (
    RUDOLF_NAME,
    RUDOLF_WORK_ACTIVITY_KIND,
    RUDOLF_WORK_EXECUTION_NORMAL,
    RUDOLF_WORK_EXECUTION_SANDBOX_PREVIEW,
    RUDOLF_WORK_PROFILE,
    RUDOLF_WORK_WORKING_PHASE,
    RudolfWorkEligibilitySnapshot,
    build_rudolf_work_result,
    evaluate_rudolf_work_capability,
    evaluate_rudolf_work_eligibility,
    evaluate_rudolf_work_preview_eligibility,
)
from .rudolf_work_settlement import RudolfWorkSettlementAdapter
from .transformation_profiles import (
    CAPABILITY_WORK,
    pet_form_allows_capability,
)


@dataclass(frozen=True)
class RudolfWorkRuntimeResult:
    handled: bool
    reason: str = ""
    activity_id: str = ""
    started: bool = False
    phase_changed: bool = False
    result_committed: bool = False
    finished: bool = False
    interrupted: bool = False


class RudolfWorkExecutor:
    def __init__(
        self,
        *,
        coordinator: ActivityCoordinator,
        runtime_adapter: ActivityRuntimeAdapter,
        settlement_adapter: RudolfWorkSettlementAdapter,
    ):
        self.coordinator = coordinator
        self.runtime_adapter = runtime_adapter
        self.settlement_adapter = settlement_adapter
        self._pending_settlement_events = {}

    def is_preview_active(self) -> bool:
        active = self.coordinator.get_activity_for_participant(
            RUDOLF_NAME
        )
        return bool(
            active is not None
            and active.spec.kind == RUDOLF_WORK_ACTIVITY_KIND
            and str(
                active.metadata.get("execution_mode", "")
            )
            == RUDOLF_WORK_EXECUTION_SANDBOX_PREVIEW
        )

    def update(
        self,
        *,
        now: float,
        world_mode: str,
        household: HouseholdState,
        event_schedule: HouseholdEventScheduleState,
        rudolf_pet,
        record_household_event,
    ) -> RudolfWorkRuntimeResult:
        now = float(now)
        if self._pending_settlement_events:
            pending_activity_id = next(
                iter(self._pending_settlement_events)
            )
            settlement_applied = self._apply_pending_settlement(
                pending_activity_id,
                record_household_event=record_household_event,
                rudolf_pet=rudolf_pet,
            )
            if not settlement_applied:
                return RudolfWorkRuntimeResult(
                    True,
                    reason="settlement_pending",
                    activity_id=pending_activity_id,
                    result_committed=True,
                )

        active = self.coordinator.get_activity_for_participant(
            RUDOLF_NAME
        )
        if active is not None:
            if active.spec.kind != RUDOLF_WORK_ACTIVITY_KIND:
                return RudolfWorkRuntimeResult(
                    False,
                    "other_activity_active",
                    activity_id=active.activity_id,
                )
            return self._update_active(
                active.activity_id,
                now=now,
                world_mode=world_mode,
                rudolf_pet=rudolf_pet,
                record_household_event=record_household_event,
            )

        if str(world_mode or "") != "golden_legend":
            return RudolfWorkRuntimeResult(
                False,
                "world_mode_disabled",
            )
        if rudolf_pet is None:
            return RudolfWorkRuntimeResult(False, "rudolf_unavailable")
        if not pet_form_allows_capability(
            rudolf_pet,
            CAPABILITY_WORK,
        ):
            return RudolfWorkRuntimeResult(False, "form_blocks_work")
        if not consume_rudolf_work_schedule_if_due(
            event_schedule,
            now=now,
        ):
            return RudolfWorkRuntimeResult(False, "schedule_not_due")

        eligibility = evaluate_rudolf_work_eligibility(
            RudolfWorkEligibilitySnapshot(
                character_name=str(
                    getattr(rudolf_pet, "name", "") or ""
                ),
                world_mode=world_mode,
                mood_score=float(
                    getattr(rudolf_pet, "mood_score", 60.0)
                ),
                living_fund=household.living_fund,
                household_pressure=household.household_pressure,
                now=now,
                next_eligible_at=0.0,
            )
        )
        if not eligibility.allowed:
            return RudolfWorkRuntimeResult(
                False,
                eligibility.reason,
            )

        return self._start_activity(
            now=now,
            rudolf_pet=rudolf_pet,
            source="household_schedule",
            execution_mode=RUDOLF_WORK_EXECUTION_NORMAL,
            extra_metadata={
                "schedule_interval_seconds": (
                    RUDOLF_WORK_INTERVAL_SECONDS
                ),
            },
        )

    def start_preview(
        self,
        *,
        now: float,
        world_mode: str,
        rudolf_pet,
    ) -> RudolfWorkRuntimeResult:
        now = float(now)
        if str(world_mode or "") != "sandbox":
            return RudolfWorkRuntimeResult(
                False,
                "preview_requires_sandbox",
            )
        if self._pending_settlement_events:
            return RudolfWorkRuntimeResult(
                False,
                "settlement_pending",
            )
        if rudolf_pet is None:
            return RudolfWorkRuntimeResult(
                False,
                "rudolf_unavailable",
            )
        if not pet_form_allows_capability(
            rudolf_pet,
            CAPABILITY_WORK,
        ):
            return RudolfWorkRuntimeResult(
                False,
                "form_blocks_work",
            )
        if self.coordinator.get_activity_for_participant(
            RUDOLF_NAME
        ) is not None:
            return RudolfWorkRuntimeResult(
                False,
                "participant_owned",
            )

        eligibility = evaluate_rudolf_work_preview_eligibility(
            RudolfWorkEligibilitySnapshot(
                character_name=str(
                    getattr(rudolf_pet, "name", "") or ""
                ),
                world_mode=world_mode,
                mood_score=float(
                    getattr(rudolf_pet, "mood_score", 60.0)
                ),
                living_fund=0,
                household_pressure=0.0,
                now=now,
            )
        )
        if not eligibility.allowed:
            return RudolfWorkRuntimeResult(
                False,
                eligibility.reason,
            )

        return self._start_activity(
            now=now,
            rudolf_pet=rudolf_pet,
            source="settings_preview",
            execution_mode=(
                RUDOLF_WORK_EXECUTION_SANDBOX_PREVIEW
            ),
        )

    def _start_activity(
        self,
        *,
        now: float,
        rudolf_pet,
        source: str,
        execution_mode: str,
        extra_metadata: dict[str, object] | None = None,
    ) -> RudolfWorkRuntimeResult:
        capability = evaluate_rudolf_work_capability(
            getattr(rudolf_pet, "asset_manager", None),
            mood_score=float(
                getattr(rudolf_pet, "mood_score", 60.0)
            ),
            resolver=self.runtime_adapter.animation_resolver,
        )
        snapshot = self.runtime_adapter.build_participant_snapshot(
            rudolf_pet,
            role=RUDOLF_WORK_PROFILE.participant_role,
            now=now,
            capability_ready=capability.ready,
            capability_reason=(
                ""
                if capability.ready
                else f"{capability.phase_name}:{capability.reason}"
            ),
        )
        start_result = self.coordinator.start(
            RUDOLF_WORK_PROFILE.activity_spec,
            owner_name=RUDOLF_NAME,
            participant_snapshots=(snapshot,),
            now=now,
            source=source,
            metadata={
                "profile_key": RUDOLF_WORK_PROFILE.profile_key,
                "work_mode": "stationary",
                "execution_mode": execution_mode,
                **dict(extra_metadata or {}),
            },
        )
        if not start_result.started:
            return RudolfWorkRuntimeResult(
                False,
                start_result.reason,
            )

        pets_by_name = {RUDOLF_NAME: rudolf_pet}
        self.runtime_adapter.apply_projections(
            pets_by_name,
            start_result.projections,
        )
        animation_result = self.runtime_adapter.apply_phase_animation(
            rudolf_pet,
            RUDOLF_WORK_PROFILE.working_animation,
        )
        if not animation_result.applied:
            interrupted = self._interrupt(
                start_result.activity_id,
                now=now,
                reason="working_animation_failed",
                rudolf_pet=rudolf_pet,
            )
            return RudolfWorkRuntimeResult(
                handled=bool(interrupted),
                reason=animation_result.reason,
                activity_id=start_result.activity_id,
                interrupted=True,
            )
        return RudolfWorkRuntimeResult(
            True,
            activity_id=start_result.activity_id,
            started=True,
        )

    def interrupt_active(
        self,
        *,
        now: float,
        reason: str,
        rudolf_pet,
    ) -> RudolfWorkRuntimeResult:
        activity = self.coordinator.get_activity_for_participant(
            RUDOLF_NAME
        )
        if activity is None:
            return RudolfWorkRuntimeResult(False, "activity_not_found")
        if activity.spec.kind != RUDOLF_WORK_ACTIVITY_KIND:
            return RudolfWorkRuntimeResult(
                False,
                "unsupported_activity",
                activity_id=activity.activity_id,
            )
        interrupted = self._interrupt(
            activity.activity_id,
            now=float(now),
            reason=reason,
            rudolf_pet=rudolf_pet,
        )
        return RudolfWorkRuntimeResult(
            handled=bool(interrupted),
            reason=reason,
            activity_id=activity.activity_id,
            interrupted=bool(interrupted),
        )

    def _update_active(
        self,
        activity_id: str,
        *,
        now: float,
        world_mode: str,
        rudolf_pet,
        record_household_event,
    ) -> RudolfWorkRuntimeResult:
        active = self.coordinator.get_activity(activity_id)
        if active is None:
            return RudolfWorkRuntimeResult(False, "activity_not_found")
        if active.spec.kind != RUDOLF_WORK_ACTIVITY_KIND:
            return RudolfWorkRuntimeResult(
                False,
                "unsupported_activity",
                activity_id=activity_id,
            )
        execution_mode = str(
            active.metadata.get(
                "execution_mode",
                RUDOLF_WORK_EXECUTION_NORMAL,
            )
        )
        expected_world_mode = (
            "sandbox"
            if execution_mode
            == RUDOLF_WORK_EXECUTION_SANDBOX_PREVIEW
            else "golden_legend"
        )
        if str(world_mode or "") != expected_world_mode:
            return self.interrupt_active(
                now=now,
                reason="world_mode_changed",
                rudolf_pet=rudolf_pet,
            )
        if rudolf_pet is None:
            interrupted = self.coordinator.interrupt(
                activity_id,
                now=now,
                reason="participant_missing",
                force=True,
            )
            return RudolfWorkRuntimeResult(
                handled=interrupted.handled,
                reason="participant_missing",
                activity_id=activity_id,
                interrupted=interrupted.handled,
            )
        is_visible = getattr(rudolf_pet, "isVisible", None)
        if (
            not bool(getattr(rudolf_pet, "user_visible", True))
            or (callable(is_visible) and not bool(is_visible()))
        ):
            return self.interrupt_active(
                now=now,
                reason="participant_hidden",
                rudolf_pet=rudolf_pet,
            )

        result_committed = active.result_committed
        if (
            execution_mode == RUDOLF_WORK_EXECUTION_NORMAL
            and active.phase.name == RUDOLF_WORK_WORKING_PHASE
            and now >= active.phase_ends_at
            and not active.result_committed
        ):
            commit_result = self.coordinator.commit_result(
                activity_id,
                now=active.phase_ends_at,
                result=build_rudolf_work_result(),
            )
            if commit_result.events:
                self._pending_settlement_events[
                    activity_id
                ] = commit_result.events[0]
            settlement_applied = self._apply_pending_settlement(
                activity_id,
                record_household_event=record_household_event,
                rudolf_pet=rudolf_pet,
            )
            if not settlement_applied:
                return RudolfWorkRuntimeResult(
                    True,
                    reason="settlement_pending",
                    activity_id=activity_id,
                    result_committed=True,
                )
            result_committed = True

        transition = self.coordinator.update(
            activity_id,
            now=now,
        )
        pets_by_name = {RUDOLF_NAME: rudolf_pet}
        if transition.projections:
            self.runtime_adapter.apply_projections(
                pets_by_name,
                transition.projections,
            )
        if transition.released_participant_names:
            self.runtime_adapter.clear_released_participants(
                pets_by_name,
                transition.released_participant_names,
                expected_activity_id=activity_id,
            )

        phase_changed = any(
            event.event_name == "activity.phase_changed"
            for event in transition.events
        )
        if phase_changed and not transition.finished:
            active = self.coordinator.get_activity(activity_id)
            binding = (
                RUDOLF_WORK_PROFILE.animation_for_phase(
                    active.phase.name
                )
                if active is not None
                else None
            )
            if binding is not None:
                animation_result = (
                    self.runtime_adapter.apply_phase_animation(
                        rudolf_pet,
                        binding,
                    )
                )
                if not animation_result.applied:
                    interrupted = self._interrupt(
                        activity_id,
                        now=now,
                        reason="phase_animation_failed",
                        rudolf_pet=rudolf_pet,
                    )
                    return RudolfWorkRuntimeResult(
                        handled=bool(interrupted),
                        reason=animation_result.reason,
                        activity_id=activity_id,
                        phase_changed=True,
                        result_committed=result_committed,
                        interrupted=True,
                    )

        return RudolfWorkRuntimeResult(
            transition.handled,
            reason=transition.reason,
            activity_id=activity_id,
            phase_changed=phase_changed,
            result_committed=(
                result_committed or transition.result_committed
            ),
            finished=transition.finished,
        )

    def _apply_pending_settlement(
        self,
        activity_id: str,
        *,
        record_household_event,
        rudolf_pet,
    ) -> bool:
        event = self._pending_settlement_events.get(activity_id)
        if event is None:
            return (
                activity_id
                in self.settlement_adapter.settled_activity_ids
            )
        apply_result = self.settlement_adapter.apply(
            event,
            record_event=record_household_event,
            apply_mood_delta=lambda mood_delta: (
                self.runtime_adapter.apply_mood_delta(
                    rudolf_pet,
                    mood_delta,
                )
            ),
        )
        if apply_result.applied:
            self._pending_settlement_events.pop(activity_id, None)
            return True
        return apply_result.reason == "activity_already_settled"

    def _interrupt(
        self,
        activity_id: str,
        *,
        now: float,
        reason: str,
        rudolf_pet,
    ) -> bool:
        transition = self.coordinator.interrupt(
            activity_id,
            now=now,
            reason=reason,
            force=True,
        )
        if transition.handled and rudolf_pet is not None:
            self.runtime_adapter.clear_released_participants(
                {RUDOLF_NAME: rudolf_pet},
                transition.released_participant_names,
                expected_activity_id=activity_id,
            )
        return transition.handled
