from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, Iterable
from uuid import uuid4

from .activity_coordinator import ActivityCoordinator
from .activity_runtime_adapter import ActivityRuntimeAdapter
from .chorus_profiles import (
    CHORUS_PROFILE,
    ChorusAnimationCapabilities,
    ChorusProfile,
    evaluate_chorus_capabilities,
)
from .chorus_rules import (
    CHORUS_ACTIVITY_KIND,
    CHORUS_APPROACH_PHASE,
    CHORUS_APPROACH_MIN_SPEED,
    CHORUS_APPROACH_SPEED_SCALE,
    CHORUS_AUDIENCE_SLOT_BASE,
    CHORUS_APPROACH_TIMEOUT_SECONDS,
    CHORUS_ARRIVAL_DISTANCE,
    CHORUS_BASE_DURATION_SECONDS,
    CHORUS_FINISH_PHASE,
    CHORUS_FINISH_SECONDS,
    CHORUS_NOTICE_MAX_DISTANCE,
    CHORUS_OBSERVE_PHASE,
    CHORUS_PERFORM_PHASE,
    CHORUS_RECONSIDER_INTERVAL_SECONDS,
    CHORUS_SLOT_GAP,
    ChorusEligibilitySnapshot,
    build_chorus_activity_spec,
    decide_chorus_reaction,
    evaluate_chorus_eligibility,
    extend_chorus_end_time,
    get_chorus_schedule_policy,
    reserve_chorus_approach_time,
)
from .chorus_state import (
    CHORUS_REACTION_AUDIENCE,
    CHORUS_REACTION_PERFORM,
    ChorusEvent,
    ChorusParticipantState,
    ChorusScheduleState,
    ChorusSessionState,
)
from .pet_random_rules import RANDOM_CONTEXT
from .pet_social_rules import child_care_need_is_active
from .transformation_profiles import (
    get_pet_form_key,
    pet_is_transforming,
)


@dataclass(frozen=True)
class ChorusRuntimeResult:
    handled: bool
    reason: str = ""
    session_id: str = ""
    participant_name: str = ""
    started: bool = False
    joined: bool = False
    removed: bool = False
    finished: bool = False
    interrupted: bool = False


class ChorusExecutor:
    def __init__(
        self,
        *,
        coordinator: ActivityCoordinator,
        runtime_adapter: ActivityRuntimeAdapter,
        profile: ChorusProfile = CHORUS_PROFILE,
        uniform: Callable[[float, float], float] | None = None,
        random_value: Callable[[], float] | None = None,
        session_id_factory: Callable[[], str] | None = None,
        frequency_provider: Callable[[], str] | None = None,
    ):
        self.coordinator = coordinator
        self.runtime_adapter = runtime_adapter
        self.profile = profile
        self.uniform = uniform or random.uniform
        self.random_value = random_value or random.random
        self.session_id_factory = session_id_factory or (lambda: uuid4().hex)
        self.frequency_provider = frequency_provider or (lambda: "normal")
        self.schedule = ChorusScheduleState()
        self.session: ChorusSessionState | None = None

    def update(
        self,
        *,
        now: float,
        pets: Iterable[object],
        world_mode: str,
        record_chorus_event=None,
    ) -> tuple[ChorusRuntimeResult, ...]:
        now = float(now)
        pets = tuple(pets or ())
        pets_by_name = self._pets_by_name(pets)
        if self.session is not None:
            result = self._update_active_session(
                now=now,
                pets=pets,
                pets_by_name=pets_by_name,
                record_chorus_event=record_chorus_event,
            )
            return (result,) if result.handled else ()

        if str(world_mode or "") not in {"sandbox", "golden_legend"}:
            self.schedule.last_wait_reason = "world_mode_disabled"
            return ()
        world_mode = str(world_mode or "")
        frequency_key = self._frequency_key()
        if self.schedule.world_mode and self.schedule.world_mode != world_mode:
            self.schedule.next_proposal_at = 0.0
        self.schedule.world_mode = world_mode
        if (
            self.schedule.frequency_key
            and self.schedule.frequency_key != frequency_key
        ):
            self.schedule.next_proposal_at = 0.0
        self.schedule.frequency_key = frequency_key
        if self.schedule.next_proposal_at <= 0.0:
            policy = get_chorus_schedule_policy(frequency_key)
            self.schedule.next_proposal_at = now + self._sample(
                policy.initial_delay_min_seconds,
                policy.initial_delay_max_seconds,
            )
            self.schedule.last_wait_reason = "initial_delay"
            return ()
        if now < self.schedule.next_proposal_at:
            return ()

        eligible = []
        for pet in pets:
            capabilities = self._capabilities(pet)
            decision = self._eligibility(
                pet,
                now=now,
                world_mode=world_mode,
                autonomous_start=True,
                capability_ready=capabilities.perform,
            )
            if decision.allowed:
                eligible.append((pet, capabilities))
        if not eligible:
            self._schedule_retry(now=now, reason="no_eligible_performer")
            return ()

        index = min(
            len(eligible) - 1,
            int(max(0.0, float(self.random_value())) * len(eligible)),
        )
        starter, capabilities = eligible[index]
        result = self._start_session(
            starter,
            capabilities=capabilities,
            now=now,
            world_mode=world_mode,
            pets=pets,
            source="autonomous",
        )
        if not result.started:
            self._schedule_retry(now=now, reason=result.reason)
            return (result,) if result.handled else ()
        self.schedule.next_proposal_at = 0.0
        self.schedule.last_wait_reason = "active"
        self._consider_reactions(
            now=now,
            world_mode=world_mode,
            pets=pets,
        )
        return (result,)

    def start_preview(
        self,
        *,
        now: float,
        world_mode: str,
        pets: Iterable[object],
    ) -> ChorusRuntimeResult:
        now = float(now)
        world_mode = str(world_mode or "")
        pets = tuple(pets or ())
        if world_mode != "sandbox":
            return ChorusRuntimeResult(False, "preview_requires_sandbox")
        if self.session is not None:
            return ChorusRuntimeResult(
                False,
                "chorus_already_active",
                session_id=self.session.session_id,
            )

        eligible = []
        for pet in pets:
            capabilities = self._capabilities(pet)
            decision = self._eligibility(
                pet,
                now=now,
                world_mode=world_mode,
                autonomous_start=True,
                capability_ready=capabilities.perform,
            )
            if decision.allowed:
                eligible.append((pet, capabilities))
        if not eligible:
            return ChorusRuntimeResult(False, "no_eligible_performer")

        index = min(
            len(eligible) - 1,
            int(max(0.0, float(self.random_value())) * len(eligible)),
        )
        starter, capabilities = eligible[index]
        result = self._start_session(
            starter,
            capabilities=capabilities,
            now=now,
            world_mode=world_mode,
            pets=pets,
            source="settings_preview",
        )
        if not result.started:
            return result
        self.schedule.world_mode = world_mode
        self.schedule.frequency_key = self._frequency_key()
        self.schedule.next_proposal_at = 0.0
        self.schedule.last_wait_reason = "active"
        self._consider_reactions(
            now=now,
            world_mode=world_mode,
            pets=pets,
        )
        return result

    def is_preview_active(self) -> bool:
        return bool(
            self.session is not None
            and self.session.source == "settings_preview"
        )

    def remove_pet(
        self,
        pet,
        *,
        now: float,
        reason: str,
        pets: Iterable[object] = (),
    ) -> ChorusRuntimeResult:
        session = self.session
        participant_name = self._pet_name(pet)
        if session is None or participant_name not in session.participants:
            return ChorusRuntimeResult(
                False,
                "participant_not_in_chorus",
                participant_name=participant_name,
            )
        self._remove_participant(
            participant_name,
            pet=pet,
            now=float(now),
            reason=reason,
        )
        if session.performer_count <= 0:
            self._release_session(
                now=float(now),
                pets_by_name=self._pets_by_name(pets),
                reason="no_performers_remaining",
            )
        return ChorusRuntimeResult(
            True,
            reason,
            session_id=session.session_id,
            participant_name=participant_name,
            removed=True,
            interrupted=True,
        )

    def interrupt_all(
        self,
        *,
        now: float,
        pets: Iterable[object],
        reason: str,
    ) -> ChorusRuntimeResult:
        session = self.session
        if session is None:
            return ChorusRuntimeResult(False, "no_active_session")
        self._release_session(
            now=float(now),
            pets_by_name=self._pets_by_name(pets),
            reason=reason,
        )
        return ChorusRuntimeResult(
            True,
            reason,
            session_id=session.session_id,
            finished=True,
            interrupted=True,
        )

    def _start_session(
        self,
        starter,
        *,
        capabilities: ChorusAnimationCapabilities,
        now: float,
        world_mode: str,
        pets: tuple[object, ...],
        source: str,
    ) -> ChorusRuntimeResult:
        session_id = str(self.session_id_factory() or "").strip()
        participant_name = self._pet_name(starter)
        if not session_id:
            return ChorusRuntimeResult(False, "empty_session_id")
        center_x = self._pet_x(starter) + (self._pet_width(starter) / 2.0)
        session = ChorusSessionState(
            session_id=session_id,
            source=str(source or "runtime"),
            world_mode=str(world_mode or ""),
            started_at=float(now),
            ends_at=float(now) + CHORUS_BASE_DURATION_SECONDS,
            center_x=float(center_x),
        )
        self.session = session
        participant = self._start_participant(
            starter,
            reaction=CHORUS_REACTION_PERFORM,
            slot=0,
            begins_with_approach=False,
            capabilities=capabilities,
            now=now,
        )
        if participant is None:
            self.session = None
            return ChorusRuntimeResult(
                True,
                "perform_animation_unavailable",
                session_id=session_id,
                participant_name=participant_name,
            )
        session.considered_names.add(participant_name)
        return ChorusRuntimeResult(
            True,
            session_id=session_id,
            participant_name=participant_name,
            started=True,
            joined=True,
        )

    def _consider_reactions(
        self,
        *,
        now: float,
        world_mode: str,
        pets: tuple[object, ...],
    ):
        session = self.session
        if session is None:
            return
        if float(now) < float(session.next_consider_at):
            return
        session.next_consider_at = (
            float(now) + CHORUS_RECONSIDER_INTERVAL_SECONDS
        )
        candidates = sorted(
            (
                pet
                for pet in pets
                if self._pet_name(pet) not in session.considered_names
            ),
            key=lambda pet: abs(
                (self._pet_x(pet) + self._pet_width(pet) / 2.0)
                - session.center_x
            ),
        )
        for pet in candidates:
            participant_name = self._pet_name(pet)
            distance = abs(
                (self._pet_x(pet) + self._pet_width(pet) / 2.0)
                - session.center_x
            )
            if distance > CHORUS_NOTICE_MAX_DISTANCE:
                continue
            decision = self._eligibility(
                pet,
                now=now,
                world_mode=world_mode,
                autonomous_start=False,
                capability_ready=True,
            )
            if not decision.allowed:
                continue
            capabilities = self._capabilities(pet)
            capability_ready = bool(
                capabilities.approach
                and (capabilities.perform or capabilities.observe)
            )
            if not capability_ready:
                continue
            reaction = decide_chorus_reaction(
                mood_score=float(getattr(pet, "mood_score", 60.0)),
                roll=self.random_value(),
                can_perform=capabilities.perform,
                can_observe=capabilities.observe,
            ).reaction
            session.considered_names.add(participant_name)
            if reaction not in {
                CHORUS_REACTION_PERFORM,
                CHORUS_REACTION_AUDIENCE,
            }:
                continue
            self._start_participant(
                pet,
                reaction=reaction,
                slot=self._allocate_next_slot(
                    session,
                    reaction,
                    preferred_side=self._preferred_slot_side(pet, session),
                ),
                begins_with_approach=True,
                capabilities=capabilities,
                now=now,
            )

    def _start_participant(
        self,
        pet,
        *,
        reaction: str,
        slot: int,
        begins_with_approach: bool,
        capabilities: ChorusAnimationCapabilities,
        now: float,
    ) -> ChorusParticipantState | None:
        session = self.session
        if session is None:
            return None
        participant_name = self._pet_name(pet)
        snapshot = self.runtime_adapter.build_participant_snapshot(
            pet,
            role=reaction,
            now=now,
            capability_ready=True,
        )
        start = self.coordinator.start(
            build_chorus_activity_spec(
                reaction,
                begins_with_approach=begins_with_approach,
            ),
            owner_name=participant_name,
            participant_snapshots=(snapshot,),
            now=now,
            source=session.source,
            metadata={
                "chorus_session_id": session.session_id,
                "chorus_reaction": reaction,
            },
        )
        if not start.started:
            return None
        self.runtime_adapter.apply_projections(
            {participant_name: pet},
            start.projections,
        )
        phase = (
            CHORUS_APPROACH_PHASE
            if begins_with_approach
            else CHORUS_PERFORM_PHASE
        )
        binding = self.profile.animation_for_phase(phase)
        animation = self.runtime_adapter.apply_phase_animation(pet, binding)
        if not animation.applied:
            cancelled = self.coordinator.cancel(
                start.activity_id,
                now=now,
                reason="animation_apply_failed",
            )
            self.runtime_adapter.clear_released_participants(
                {participant_name: pet},
                cancelled.released_participant_names,
                expected_activity_id=start.activity_id,
            )
            return None
        participant = ChorusParticipantState(
            name=participant_name,
            reaction=reaction,
            activity_id=start.activity_id,
            phase=phase,
            slot=int(slot),
            joined_at=float(now),
            approach_deadline_at=(
                float(now) + CHORUS_APPROACH_TIMEOUT_SECONDS
                if begins_with_approach
                else 0.0
            ),
        )
        session.participants[participant_name] = participant
        session.participant_roles[participant_name] = reaction
        if begins_with_approach:
            session.ends_at = reserve_chorus_approach_time(
                started_at=session.started_at,
                current_ends_at=session.ends_at,
                now=now,
            )
        return participant

    def _update_active_session(
        self,
        *,
        now: float,
        pets: tuple[object, ...],
        pets_by_name: dict[str, object],
        record_chorus_event,
    ) -> ChorusRuntimeResult:
        session = self.session
        if session is None:
            return ChorusRuntimeResult(False, "no_active_session")

        emergency_reason = self._emergency_reason(pets)
        if emergency_reason:
            event = self._build_event(
                session,
                now=now,
                event_type="chorus_interrupted",
                outcome="interrupted",
                reason=emergency_reason,
            )
            self._release_session(
                now=now,
                pets_by_name=pets_by_name,
                reason=emergency_reason,
            )
            if callable(record_chorus_event):
                record_chorus_event(event)
            return ChorusRuntimeResult(
                True,
                emergency_reason,
                session_id=session.session_id,
                finished=True,
                interrupted=True,
            )

        for participant_name in tuple(session.participants):
            participant = session.participants.get(participant_name)
            pet = pets_by_name.get(participant_name)
            activity = (
                self.coordinator.get_activity(participant.activity_id)
                if participant is not None
                else None
            )
            if (
                participant is None
                or activity is None
                or not self._pet_is_visible(pet)
                or bool(getattr(pet, "dragging", False))
                or pet_is_transforming(pet)
            ):
                self._remove_participant(
                    participant_name,
                    pet=pet,
                    now=now,
                    reason="participant_unavailable",
                )

        if session.finishing:
            if now < session.finish_ends_at:
                return ChorusRuntimeResult(False, "finishing")
            event = self._build_event(
                session,
                now=now,
                event_type="chorus_completed",
                outcome="completed",
            )
            self._release_session(
                now=now,
                pets_by_name=pets_by_name,
                reason="completed",
                complete=True,
            )
            if callable(record_chorus_event):
                record_chorus_event(event)
            return ChorusRuntimeResult(
                True,
                "completed",
                session_id=session.session_id,
                finished=True,
            )

        if not session.participants or session.performer_count <= 0:
            event = self._build_event(
                session,
                now=now,
                event_type="chorus_interrupted",
                outcome="interrupted",
                reason="no_performers_remaining",
            )
            self._release_session(
                now=now,
                pets_by_name=pets_by_name,
                reason="no_performers_remaining",
            )
            if callable(record_chorus_event):
                record_chorus_event(event)
            return ChorusRuntimeResult(
                True,
                "no_performers_remaining",
                session_id=session.session_id,
                finished=True,
                interrupted=True,
            )

        if now >= session.ends_at:
            self._begin_finishing(now=now, pets_by_name=pets_by_name)
            return ChorusRuntimeResult(
                True,
                "finishing",
                session_id=session.session_id,
            )

        self._consider_reactions(
            now=now,
            world_mode=session.world_mode,
            pets=pets,
        )

        for participant_name in tuple(session.participants):
            participant = session.participants.get(participant_name)
            if participant is None or participant.phase != CHORUS_APPROACH_PHASE:
                continue
            pet = pets_by_name.get(participant_name)
            if now >= participant.approach_deadline_at:
                self._remove_participant(
                    participant_name,
                    pet=pet,
                    now=now,
                    reason="approach_timeout",
                )
                continue
            target_x = self._slot_target_x(
                pet,
                participant.slot,
                pets_by_name=pets_by_name,
            )
            if self._move_pet(pet, target_x):
                self._arrive_participant(participant, pet=pet, now=now)

        if session.performer_count <= 0:
            return ChorusRuntimeResult(False, "no_performers_remaining")
        return ChorusRuntimeResult(False, "active")

    def _arrive_participant(
        self,
        participant: ChorusParticipantState,
        *,
        pet,
        now: float,
    ):
        target_phase = (
            CHORUS_PERFORM_PHASE
            if participant.is_performer
            else CHORUS_OBSERVE_PHASE
        )
        transition = self.coordinator.transition_to_phase(
            participant.activity_id,
            phase_name=target_phase,
            now=now,
            reason="chorus_slot_reached",
        )
        if not transition.handled:
            self._remove_participant(
                participant.name,
                pet=pet,
                now=now,
                reason=transition.reason,
            )
            return
        self.runtime_adapter.apply_projections(
            {participant.name: pet},
            transition.projections,
        )
        animation = self.runtime_adapter.apply_phase_animation(
            pet,
            self.profile.animation_for_phase(target_phase),
        )
        if not animation.applied:
            self._remove_participant(
                participant.name,
                pet=pet,
                now=now,
                reason="arrival_animation_failed",
            )
            return
        participant.phase = target_phase
        participant.approach_deadline_at = 0.0
        self._face_session_center(pet)
        if participant.is_performer and self.session is not None:
            self.session.ends_at = extend_chorus_end_time(
                started_at=self.session.started_at,
                current_ends_at=self.session.ends_at,
                now=now,
                performer_count=self.session.performer_count,
            )

    def _begin_finishing(
        self,
        *,
        now: float,
        pets_by_name: dict[str, object],
    ):
        session = self.session
        if session is None:
            return
        session.finishing = True
        session.finish_ends_at = float(now) + CHORUS_FINISH_SECONDS
        for participant_name in tuple(session.participants):
            participant = session.participants.get(participant_name)
            pet = pets_by_name.get(participant_name)
            if participant is None or pet is None:
                continue
            capabilities = self._capabilities(pet)
            if not capabilities.finish:
                self._finish_participant(
                    participant_name,
                    pet=pet,
                    now=now,
                    reason="finish_animation_unavailable",
                )
                continue
            transition = self.coordinator.transition_to_phase(
                participant.activity_id,
                phase_name=CHORUS_FINISH_PHASE,
                now=now,
                reason="chorus_synchronized_finish",
            )
            if not transition.handled:
                self._finish_participant(
                    participant_name,
                    pet=pet,
                    now=now,
                    reason=transition.reason,
                )
                continue
            self.runtime_adapter.apply_projections(
                {participant_name: pet},
                transition.projections,
            )
            animation = self.runtime_adapter.apply_phase_animation(
                pet,
                self.profile.finish_animation,
            )
            if animation.applied:
                participant.phase = CHORUS_FINISH_PHASE
            else:
                self._finish_participant(
                    participant_name,
                    pet=pet,
                    now=now,
                    reason="finish_animation_apply_failed",
                )

    def _finish_participant(self, participant_name, *, pet, now, reason):
        session = self.session
        participant = (
            session.participants.get(participant_name)
            if session is not None
            else None
        )
        if participant is None:
            return
        transition = self.coordinator.finish(
            participant.activity_id,
            now=now,
            reason=reason,
        )
        self.runtime_adapter.clear_released_participants(
            {participant_name: pet},
            transition.released_participant_names,
            expected_activity_id=participant.activity_id,
        )
        session.participants.pop(participant_name, None)

    def _remove_participant(self, participant_name, *, pet, now, reason):
        session = self.session
        participant = (
            session.participants.get(participant_name)
            if session is not None
            else None
        )
        if participant is None:
            return
        transition = self.coordinator.interrupt(
            participant.activity_id,
            now=now,
            reason=str(reason or "participant_removed"),
            force=True,
        )
        self.runtime_adapter.clear_released_participants(
            {participant_name: pet},
            transition.released_participant_names,
            expected_activity_id=participant.activity_id,
        )
        session.participants.pop(participant_name, None)
        session.considered_names.add(participant_name)
        session.participant_roles.pop(participant_name, None)
        if pet is not None and self._pet_is_visible(pet):
            self._restore_ambient(pet)

    def _release_session(
        self,
        *,
        now: float,
        pets_by_name: dict[str, object],
        reason: str,
        complete: bool = False,
    ):
        session = self.session
        if session is None:
            return
        for participant_name in tuple(session.participants):
            participant = session.participants.get(participant_name)
            if participant is None:
                continue
            pet = pets_by_name.get(participant_name)
            transition = (
                self.coordinator.finish(
                    participant.activity_id,
                    now=now,
                    reason=reason,
                )
                if complete
                else self.coordinator.interrupt(
                    participant.activity_id,
                    now=now,
                    reason=reason,
                    force=True,
                )
            )
            self.runtime_adapter.clear_released_participants(
                {participant_name: pet},
                transition.released_participant_names,
                expected_activity_id=participant.activity_id,
            )
            if pet is not None and self._pet_is_visible(pet):
                self._restore_ambient(pet)
        self.schedule.last_finished_at = float(now)
        policy = self._schedule_policy()
        self.schedule.next_proposal_at = float(now) + self._sample(
            policy.cooldown_min_seconds,
            policy.cooldown_max_seconds,
        )
        self.schedule.last_wait_reason = "cooldown"
        self.session = None

    def _eligibility(
        self,
        pet,
        *,
        now: float,
        world_mode: str,
        autonomous_start: bool,
        capability_ready: bool,
    ):
        snapshot = self.runtime_adapter.build_participant_snapshot(
            pet,
            role=CHORUS_REACTION_PERFORM,
            now=now,
            capability_ready=capability_ready,
        )
        return evaluate_chorus_eligibility(
            ChorusEligibilitySnapshot(
                character_name=self._pet_name(pet),
                form_key=get_pet_form_key(pet),
                world_mode=world_mode,
                mood_score=float(getattr(pet, "mood_score", 60.0)),
                visible=snapshot.visible,
                enabled=snapshot.enabled,
                grounded=(
                    float(getattr(pet, "vy", 0.0) or 0.0) == 0.0
                    and str(getattr(pet, "flight_mode", "none") or "none")
                    == "none"
                    and not bool(getattr(pet, "perched_window_hwnd", 0))
                ),
                busy=bool(snapshot.active_activity_id or snapshot.busy_reasons),
                capability_ready=capability_ready,
            ),
            autonomous_start=autonomous_start,
        )

    def _capabilities(self, pet) -> ChorusAnimationCapabilities:
        return evaluate_chorus_capabilities(
            getattr(pet, "asset_manager", None),
            mood_score=float(getattr(pet, "mood_score", 60.0)),
            resolver=self.runtime_adapter.animation_resolver,
            profile=self.profile,
        )

    def _emergency_reason(self, pets: tuple[object, ...]) -> str:
        for pet in pets:
            name = self._pet_name(pet)
            if (
                name == "Tsurumaru Tsuyoshi"
                and str(getattr(pet, "held_item_kind", "") or "") == "honey"
            ):
                return "tsuyoshi_honey_guard_needed"
            care_enabled = getattr(pet, "is_care_feature_enabled", None)
            is_distressed = getattr(pet, "is_distressed", None)
            if child_care_need_is_active(
                is_child=not bool(getattr(pet, "is_adult", False)),
                is_visible=self._pet_is_visible(pet),
                care_enabled=(
                    bool(care_enabled()) if callable(care_enabled) else True
                ),
                is_recovering=bool(getattr(pet, "is_recovering", False)),
                is_distressed=(
                    bool(is_distressed()) if callable(is_distressed) else False
                ),
            ):
                return "child_care_needed"
        return ""

    def _build_event(
        self,
        session: ChorusSessionState,
        *,
        now: float,
        event_type: str,
        outcome: str,
        reason: str = "",
    ) -> ChorusEvent:
        return ChorusEvent(
            session_id=session.session_id,
            event_type=event_type,
            occurred_at=float(now),
            started_at=session.started_at,
            source=session.source,
            world_mode=session.world_mode,
            participant_roles=tuple(session.participant_roles.items()),
            outcome=outcome,
            reason=reason,
        )

    def _schedule_retry(self, *, now: float, reason: str):
        policy = self._schedule_policy()
        self.schedule.next_proposal_at = float(now) + self._sample(
            policy.retry_min_seconds,
            policy.retry_max_seconds,
        )
        self.schedule.last_wait_reason = str(reason or "retry")

    def _schedule_policy(self):
        return get_chorus_schedule_policy(self._frequency_key())

    def _frequency_key(self):
        try:
            frequency_key = self.frequency_provider()
        except Exception:
            frequency_key = "normal"
        return str(frequency_key or "normal")

    def _sample(self, minimum: float, maximum: float) -> float:
        return max(
            float(minimum),
            min(float(maximum), float(self.uniform(minimum, maximum))),
        )

    def _allocate_next_slot(
        self,
        session: ChorusSessionState,
        reaction: str = CHORUS_REACTION_PERFORM,
        *,
        preferred_side: int = 0,
    ) -> int:
        is_audience = reaction == CHORUS_REACTION_AUDIENCE
        normalized_side = (
            1 if preferred_side > 0 else
            -1 if preferred_side < 0 else
            0
        )
        if normalized_side:
            used_slots = {
                int(participant.slot)
                for participant in session.participants.values()
            }
            if is_audience:
                performer_distances = [
                    abs(int(participant.slot))
                    for participant in session.participants.values()
                    if participant.is_performer
                    and int(participant.slot) * normalized_side > 0
                ]
                distance = max(
                    CHORUS_AUDIENCE_SLOT_BASE,
                    max(performer_distances, default=0) + 1,
                )
            else:
                distance = 1
                performer_slots = {
                    int(participant.slot)
                    for participant in session.participants.values()
                    if participant.is_performer
                }
                while normalized_side * distance in performer_slots:
                    distance += 1
                self._shift_audiences_outward(
                    session,
                    side=normalized_side,
                    starting_distance=distance,
                )
                used_slots = {
                    int(participant.slot)
                    for participant in session.participants.values()
                }
            while normalized_side * distance in used_slots:
                distance += 1
            ordinal_field = (
                "next_audience_slot_ordinal"
                if is_audience else
                "next_performer_slot_ordinal"
            )
            setattr(
                session,
                ordinal_field,
                max(
                    1,
                    int(getattr(session, ordinal_field, 1)),
                ) + 1,
            )
            return normalized_side * distance
        ordinal_field = (
            "next_audience_slot_ordinal"
            if is_audience else
            "next_performer_slot_ordinal"
        )
        ordinal = max(1, int(getattr(session, ordinal_field, 1)))
        setattr(session, ordinal_field, ordinal + 1)
        distance = (ordinal + 1) // 2
        if is_audience:
            distance += CHORUS_AUDIENCE_SLOT_BASE - 1
        return distance if ordinal % 2 else -distance

    @staticmethod
    def _shift_audiences_outward(
        session: ChorusSessionState,
        *,
        side: int,
        starting_distance: int,
    ) -> None:
        audiences = sorted(
            (
                participant
                for participant in session.participants.values()
                if not participant.is_performer
                and int(participant.slot) * int(side) > 0
                and abs(int(participant.slot)) >= int(starting_distance)
            ),
            key=lambda participant: abs(int(participant.slot)),
            reverse=True,
        )
        for participant in audiences:
            participant.slot = int(participant.slot) + int(side)

    def _preferred_slot_side(
        self,
        pet,
        session: ChorusSessionState,
    ) -> int:
        if pet is None:
            return 0
        pet_center = self._pet_x(pet) + self._pet_width(pet) / 2.0
        if pet_center < float(session.center_x):
            return -1
        if pet_center > float(session.center_x):
            return 1
        return 0

    def _slot_target_x(self, pet, slot: int, *, pets_by_name) -> float:
        session = self.session
        if session is None:
            return self._pet_x(pet)
        maximum_width = max(
            [self._stage_footprint_width(pet)]
            + [
                self._stage_footprint_width(pets_by_name.get(name))
                for name in session.participants
                if pets_by_name.get(name) is not None
            ]
        )
        target_center = session.center_x + int(slot) * (
            maximum_width + CHORUS_SLOT_GAP
        )
        target_x = target_center - self._pet_width(pet) / 2.0
        clamp = getattr(pet, "clamp_x_to_virtual_geometry", None)
        if callable(clamp):
            target_x = clamp(target_x, self._pet_width(pet), padding=8)
        return float(target_x)

    def _move_pet(self, pet, target_x: float) -> bool:
        if pet is None:
            return False
        pet.direction = 1 if float(target_x) >= self._pet_x(pet) else -1
        mover = getattr(pet, "move_toward_x", None)
        if callable(mover):
            arrived = bool(
                mover(
                    float(target_x),
                    speed_scale=CHORUS_APPROACH_SPEED_SCALE,
                    min_speed=CHORUS_APPROACH_MIN_SPEED,
                )
            )
        else:
            arrived = False
        return arrived or abs(self._pet_x(pet) - float(target_x)) <= CHORUS_ARRIVAL_DISTANCE

    @classmethod
    def _stage_footprint_width(cls, pet) -> float:
        radius = max(0.0, float(getattr(pet, "radius", 0.0) or 0.0))
        if radius > 0.0:
            return radius * 2.0
        return min(cls._pet_width(pet), 240.0)

    def _face_session_center(self, pet):
        if self.session is None or pet is None:
            return
        pet_center = self._pet_x(pet) + self._pet_width(pet) / 2.0
        pet.direction = -1 if self.session.center_x < pet_center else 1

    @staticmethod
    def _restore_ambient(pet):
        pet.state = "idle"
        pet.state_timer = 0
        changed = False
        change_for_context = getattr(
            pet,
            "change_state_for_context_with_preferences",
            None,
        )
        if callable(change_for_context):
            changed = bool(change_for_context("idle", RANDOM_CONTEXT))
        if not changed:
            apply_random_idle = getattr(pet, "apply_random_idle_animation", None)
            if callable(apply_random_idle):
                apply_random_idle()
        refresh = getattr(pet, "refresh_movement_state", None)
        if callable(refresh):
            refresh()

    @staticmethod
    def _pet_name(pet) -> str:
        return str(getattr(pet, "name", "") or "").strip()

    @classmethod
    def _pets_by_name(cls, pets: Iterable[object]) -> dict[str, object]:
        return {
            cls._pet_name(pet): pet
            for pet in pets or ()
            if cls._pet_name(pet)
        }

    @staticmethod
    def _pet_is_visible(pet) -> bool:
        if pet is None or not bool(getattr(pet, "user_visible", True)):
            return False
        is_visible = getattr(pet, "isVisible", None)
        return bool(is_visible()) if callable(is_visible) else True

    @staticmethod
    def _pet_x(pet) -> float:
        getter = getattr(pet, "x", None)
        return float(getter() if callable(getter) else getattr(pet, "x", 0.0))

    @staticmethod
    def _pet_width(pet) -> float:
        if pet is None:
            return 100.0
        getter = getattr(pet, "width", None)
        return max(
            1.0,
            float(
                getter()
                if callable(getter)
                else getattr(pet, "width", 100.0)
            ),
        )
