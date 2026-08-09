from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable, Iterable, Mapping

from .activity_coordinator import ActivityCoordinator
from .activity_runtime_adapter import ActivityRuntimeAdapter
from .pet_intent_rules import (
    INTENT_AMBIENT_IDLE,
    INTENT_SLEEP_JOIN_APPROACH,
    INTENT_SLEEP_OBSERVE,
    SLEEP_JOIN_INTENT_KINDS,
)
from .sleep_care_rules import (
    SIRIUS_SYMBOLI_NAME,
    SleepingCaregiverCandidate,
    choose_sleeping_caregiver_to_wake,
)
from .sleep_join_rules import (
    SLEEP_JOIN_PHASE_APPROACHING,
    SLEEP_JOIN_PHASE_OBSERVING,
    SleepJoinAttemptState,
    build_sleep_group_join_plan,
    resolve_sleep_join_target_x,
)
from .sleep_profiles import (
    SLEEP_PROFILE,
    SleepProfile,
    evaluate_sleep_capability,
    evaluate_sleep_join_capability,
)
from .sleep_rules import (
    SLEEP_ACTIVITY_KIND,
    SLEEP_COOLDOWN_MAX_SECONDS,
    SLEEP_COOLDOWN_MIN_SECONDS,
    SLEEP_DURATION_MAX_SECONDS,
    SLEEP_DURATION_MIN_SECONDS,
    SLEEP_INITIAL_DELAY_MAX_SECONDS,
    SLEEP_INITIAL_DELAY_MIN_SECONDS,
    SLEEP_INTERRUPTED_COOLDOWN_MAX_SECONDS,
    SLEEP_INTERRUPTED_COOLDOWN_MIN_SECONDS,
    SLEEP_JOIN_ARRIVAL_DISTANCE,
    SLEEP_JOIN_MOVE_SPEED_SCALE,
    SLEEP_MAX_CONCURRENT,
    SLEEP_OBSERVE_MAX_SECONDS,
    SLEEP_OBSERVE_MIN_SECONDS,
    SLEEP_RETRY_MAX_SECONDS,
    SLEEP_RETRY_MIN_SECONDS,
    SLEEP_SOCIAL_PROBE_MAX_SECONDS,
    SLEEP_SOCIAL_PROBE_MIN_SECONDS,
    SLEEP_SOCIAL_RETRY_MAX_SECONDS,
    SLEEP_SOCIAL_RETRY_MIN_SECONDS,
    SLEEP_TRIGGER_AUTONOMOUS,
    SLEEP_TRIGGER_OBSERVED_JOIN,
    SLEEP_TRIGGER_SANDBOX_CONTROL,
    SLEEP_WAKING_PHASE,
    SLEEPING_PHASE,
    SleepEligibilitySnapshot,
    SleepJoinCandidateSnapshot,
    SleepJoinInfluenceSnapshot,
    SleepScheduleState,
    evaluate_sleep_eligibility,
    evaluate_sleep_join_candidate,
    evaluate_sleep_join_influence,
)
from .transformation_profiles import (
    CAPABILITY_CARE_GIVER,
    CAPABILITY_SLEEP,
    pet_form_allows_capability,
)


@dataclass(frozen=True)
class SleepRuntimeResult:
    handled: bool
    reason: str = ""
    activity_id: str = ""
    participant_name: str = ""
    started: bool = False
    phase_changed: bool = False
    finished: bool = False
    interrupted: bool = False
    metadata: Mapping[str, object] = field(default_factory=dict)


class SleepExecutor:
    def __init__(
        self,
        *,
        coordinator: ActivityCoordinator,
        runtime_adapter: ActivityRuntimeAdapter,
        profile: SleepProfile = SLEEP_PROFILE,
        uniform: Callable[[float, float], float] | None = None,
        random_value: Callable[[], float] | None = None,
        max_concurrent_sleepers: int | None = None,
    ):
        self.coordinator = coordinator
        self.runtime_adapter = runtime_adapter
        self.profile = profile
        self.uniform = uniform or random.uniform
        self.random_value = random_value or random.random
        configured_capacity = (
            SLEEP_MAX_CONCURRENT
            if max_concurrent_sleepers is None
            else int(max_concurrent_sleepers)
        )
        self.max_concurrent_sleepers = (
            configured_capacity if configured_capacity > 0 else None
        )
        self.schedules: dict[str, SleepScheduleState] = {}
        self.join_attempts: dict[str, SleepJoinAttemptState] = {}

    def update(
        self,
        *,
        now: float,
        pets: Iterable[object],
        world_mode: str,
    ) -> tuple[SleepRuntimeResult, ...]:
        now = float(now)
        pets = tuple(pets or ())
        pets_by_name = self._pets_by_name(pets)
        results = []
        sleep_capacity = self._resolve_sleep_capacity(pets)

        care_wake_result = self._wake_sleeping_caregiver_for_distress(
            now=now,
            pets=pets,
        )
        if care_wake_result.handled:
            results.append(care_wake_result)

        active_sleep_activities = tuple(
            activity
            for activity in self.coordinator.get_active_activities()
            if activity.spec.kind == SLEEP_ACTIVITY_KIND
        )
        for activity in active_sleep_activities:
            participant_name = activity.participants[0].name
            result = self._update_active(
                activity.activity_id,
                now=now,
                world_mode=world_mode,
                pet=pets_by_name.get(participant_name),
            )
            if result.handled:
                results.append(result)

        for pet in pets:
            participant_name = self._pet_name(pet)
            if participant_name:
                self._ensure_schedule(participant_name, now=now)

        self._prune_join_attempts(now=now, pets_by_name=pets_by_name)

        active_sleep_count = self._active_sleep_count()
        due_pets = sorted(
            (pet for pet in pets if self._is_due(pet, now=now)),
            key=lambda pet: self.schedules[
                self._pet_name(pet)
            ].next_proposal_at,
        )
        for pet in due_pets:
            participant_name = self._pet_name(pet)
            if not pet_form_allows_capability(
                pet,
                CAPABILITY_SLEEP,
            ):
                self._schedule_retry(participant_name, now=now)
                continue
            decision = evaluate_sleep_eligibility(
                SleepEligibilitySnapshot(
                    participant_name=participant_name,
                    now=now,
                    next_proposal_at=self.schedules[
                        participant_name
                    ].next_proposal_at,
                    active_sleep_count=active_sleep_count,
                    max_concurrent_sleepers=(
                        sleep_capacity
                    ),
                )
            )
            if not decision.allowed:
                self._schedule_retry(participant_name, now=now)
                continue
            result = self._start_sleep(
                pet,
                now=now,
                world_mode=world_mode,
                trigger_kind=SLEEP_TRIGGER_AUTONOMOUS,
            )
            if result.started:
                results.append(result)
                active_sleep_count += 1
            else:
                self._schedule_retry(participant_name, now=now)

        self._start_due_sleep_observations(
            now=now,
            pets=pets,
            sleep_capacity=sleep_capacity,
        )
        return tuple(results)

    def request_sandbox_toggle(
        self,
        pet,
        *,
        now: float,
        world_mode: str,
        pets: Iterable[object],
    ) -> SleepRuntimeResult:
        now = float(now)
        participant_name = self._pet_name(pet)
        if str(world_mode or "") != "sandbox":
            return SleepRuntimeResult(
                False,
                "sandbox_required",
                participant_name=participant_name,
            )
        if pet is None or not participant_name:
            return SleepRuntimeResult(
                False,
                "participant_unavailable",
                participant_name=participant_name,
            )
        activity = self._sleep_activity_for_pet(pet)
        if activity is not None:
            return self.request_early_wake(
                pet,
                now=now,
                reason=SLEEP_TRIGGER_SANDBOX_CONTROL,
            )
        pets = tuple(pets or ())
        sleep_capacity = self._resolve_sleep_capacity(pets)
        if (
            sleep_capacity > 0
            and self._active_sleep_count() >= sleep_capacity
        ):
            return SleepRuntimeResult(
                False,
                "sleep_capacity_reached",
                participant_name=participant_name,
            )
        return self._start_sleep(
            pet,
            now=now,
            world_mode=world_mode,
            trigger_kind=SLEEP_TRIGGER_SANDBOX_CONTROL,
        )

    def update_join_behavior(
        self,
        pet,
        all_pets: Iterable[object],
        *,
        now: float,
        world_mode: str,
    ) -> bool:
        now = float(now)
        participant_name = self._pet_name(pet)
        attempt = self.join_attempts.get(participant_name)
        if attempt is None:
            return False
        all_pets = tuple(all_pets or ())
        pets_by_name = self._pets_by_name(all_pets)
        if not self._observer_can_continue(pet, now=now):
            self._cancel_join_attempt(
                participant_name,
                pet=pet,
                now=now,
                retry=True,
            )
            return False

        target_pet = pets_by_name.get(attempt.target_name)
        target_activity = self._sleeping_activity_for_pet(target_pet)
        if (
            target_activity is None
            or target_activity.activity_id != attempt.target_activity_id
        ):
            self._cancel_join_attempt(
                participant_name,
                pet=pet,
                now=now,
                retry=True,
            )
            return False

        if attempt.phase == SLEEP_JOIN_PHASE_OBSERVING:
            if not attempt.animation_applied:
                animation = self.runtime_adapter.apply_phase_animation(
                    pet,
                    self.profile.observing_animation,
                )
                if not animation.applied:
                    self._cancel_join_attempt(
                        participant_name,
                        pet=pet,
                        now=now,
                        retry=True,
                    )
                    return False
                attempt.animation_applied = True
            self._face_pet(pet, target_pet)
            if now < attempt.phase_ends_at:
                return True
            if not self._should_join_after_observing(
                pet,
                target_pet,
                target_activity,
                now=now,
            ):
                self._cancel_join_attempt(
                    participant_name,
                    pet=pet,
                    now=now,
                    retry=True,
                )
                return False
            plan = self._build_group_join_plan(target_activity)
            if not plan.allowed:
                self._cancel_join_attempt(
                    participant_name,
                    pet=pet,
                    now=now,
                    retry=True,
                )
                return False
            attempt.phase = SLEEP_JOIN_PHASE_APPROACHING
            attempt.phase_ends_at = 0.0
            attempt.group_id = plan.group_id
            attempt.anchor_name = plan.anchor_name
            attempt.slot = plan.slot
            attempt.animation_applied = False
            self._set_join_intent(pet, attempt, now=now)

        if attempt.phase != SLEEP_JOIN_PHASE_APPROACHING:
            return True
        if not attempt.animation_applied:
            animation = self.runtime_adapter.apply_phase_animation(
                pet,
                self.profile.join_approach_animation,
            )
            if not animation.applied:
                self._cancel_join_attempt(
                    participant_name,
                    pet=pet,
                    now=now,
                    retry=True,
                )
                return False
            attempt.animation_applied = True

        anchor_pet = pets_by_name.get(attempt.anchor_name) or target_pet
        if self._sleep_activity_for_pet(anchor_pet) is None:
            self._cancel_join_attempt(
                participant_name,
                pet=pet,
                now=now,
                retry=True,
            )
            return False
        target_x = self._resolve_join_target_x(
            pet,
            anchor_pet,
            slot=attempt.slot,
        )
        mover = getattr(pet, "move_toward_x", None)
        if not callable(mover):
            self._cancel_join_attempt(
                participant_name,
                pet=pet,
                now=now,
                retry=True,
            )
            return False
        arrived = bool(
            mover(
                target_x,
                speed_scale=SLEEP_JOIN_MOVE_SPEED_SCALE,
            )
        ) or abs(float(self._pet_x(pet)) - float(target_x)) <= (
            SLEEP_JOIN_ARRIVAL_DISTANCE
        )
        if not arrived:
            return True

        current_target_activity = self._sleeping_activity_for_pet(target_pet)
        sleep_capacity = self._resolve_sleep_capacity(all_pets)
        if (
            current_target_activity is None
            or (
                sleep_capacity > 0
                and self._active_sleep_count() >= sleep_capacity
            )
        ):
            self._cancel_join_attempt(
                participant_name,
                pet=pet,
                now=now,
                retry=True,
            )
            return False

        self.join_attempts.pop(participant_name, None)
        self._clear_join_intent(pet, now=now)
        result = self._start_sleep(
            pet,
            now=now,
            world_mode=world_mode,
            trigger_kind=SLEEP_TRIGGER_OBSERVED_JOIN,
            group_id=attempt.group_id,
            anchor_name=attempt.anchor_name,
            group_slot=attempt.slot,
            target_activity_id=attempt.target_activity_id,
        )
        if not result.started:
            self._schedule_social_retry(participant_name, now=now)
        return True

    def request_early_wake(
        self,
        pet,
        *,
        now: float,
        reason: str,
        care_target_name: str = "",
    ) -> SleepRuntimeResult:
        now = float(now)
        participant_name = self._pet_name(pet)
        activity = self._sleep_activity_for_pet(pet)
        if activity is None:
            return SleepRuntimeResult(
                False,
                "sleep_activity_not_found",
                participant_name=participant_name,
            )
        if activity.phase.name == SLEEP_WAKING_PHASE:
            return SleepRuntimeResult(
                False,
                "already_waking",
                activity_id=activity.activity_id,
                participant_name=participant_name,
            )

        group_id = str(
            activity.metadata.get("sleep_group_id", "") or ""
        )
        activity.metadata["early_wake_reason"] = str(reason or "")
        activity.metadata["care_wake_target_name"] = str(
            care_target_name or ""
        )
        transition = self.coordinator.transition_to_phase(
            activity.activity_id,
            phase_name=SLEEP_WAKING_PHASE,
            now=now,
            reason=str(reason or "early_wake"),
        )
        if not transition.handled:
            return SleepRuntimeResult(
                False,
                transition.reason,
                activity_id=activity.activity_id,
                participant_name=participant_name,
            )
        self.runtime_adapter.apply_projections(
            {participant_name: pet},
            transition.projections,
        )
        animation = self.runtime_adapter.apply_phase_animation(
            pet,
            self.profile.waking_animation,
        )
        if not animation.applied:
            return self._interrupt(
                activity.activity_id,
                pet=pet,
                now=now,
                reason="early_wake_animation_failed",
            )

        if group_id:
            activity.metadata["sleep_group_id"] = ""
            activity.metadata["sleep_anchor_name"] = ""
            activity.metadata["sleep_group_slot"] = 0
            self._reanchor_sleep_group(group_id)
        return SleepRuntimeResult(
            True,
            reason=str(reason or "early_wake"),
            activity_id=activity.activity_id,
            participant_name=participant_name,
            phase_changed=True,
            metadata=self._achievement_metadata(activity),
        )

    def _wake_sleeping_caregiver_for_distress(
        self,
        *,
        now: float,
        pets: tuple[object, ...],
    ) -> SleepRuntimeResult:
        adults = tuple(
            pet
            for pet in pets
            if pet_form_allows_capability(
                pet,
                CAPABILITY_CARE_GIVER,
            )
            and self._pet_is_visible(pet)
        )
        children = []
        for pet in pets:
            if (
                pet_form_allows_capability(
                    pet,
                    CAPABILITY_CARE_GIVER,
                )
                or not self._pet_is_visible(pet)
                or bool(getattr(pet, "is_recovering", False))
                or getattr(pet, "care_partner", None) is not None
                or self.coordinator.get_activity_for_participant(
                    self._pet_name(pet)
                )
                is not None
            ):
                continue
            care_blocked = getattr(
                pet,
                "is_care_blocked_by_negative_afterglow",
                None,
            )
            if callable(care_blocked) and bool(care_blocked(now)):
                continue
            is_distressed = getattr(pet, "is_distressed", None)
            if not callable(is_distressed) or not bool(is_distressed()):
                continue
            mood_score = float(getattr(pet, "mood_score", 100.0))
            mood_tag = str(getattr(pet, "current_mood_tag", "") or "")
            severe = mood_score < 20.0 or mood_tag in {
                "cry",
                "hard-cry",
            }
            children.append((not severe, mood_score, self._pet_name(pet), pet))
        if not children or not adults:
            return SleepRuntimeResult(False, "care_wake_not_needed")
        children.sort(key=lambda item: item[:3])
        child = children[0][3]
        child_name = self._pet_name(child)

        if child_name in self.join_attempts:
            self._cancel_join_attempt(
                child_name,
                pet=child,
                now=now,
                retry=True,
            )

        for adult in adults:
            adult_name = self._pet_name(adult)
            if adult_name in self.join_attempts:
                self._cancel_join_attempt(
                    adult_name,
                    pet=adult,
                    now=now,
                    retry=True,
                )

        for adult in adults:
            activity = self._sleep_activity_for_pet(adult)
            if (
                activity is not None
                and activity.phase.name == SLEEP_WAKING_PHASE
                and str(
                    activity.metadata.get("early_wake_reason", "") or ""
                ) == "child_distress"
            ):
                return SleepRuntimeResult(False, "care_wake_pending")
            if getattr(adult, "care_mode", "none") != "none":
                return SleepRuntimeResult(False, "caregiver_responding")

        awake_available = any(
            self._awake_caregiver_available(
                adult,
                child,
                now=now,
            )
            for adult in adults
        )
        sleeping_candidates = []
        for adult in adults:
            activity = self._sleep_activity_for_pet(adult)
            if (
                activity is None
                or activity.phase.name == SLEEP_WAKING_PHASE
                or not self._caregiver_in_range(adult, child)
                or bool(getattr(adult, "dragging", False))
                or bool(getattr(adult, "is_angry_locked", False))
            ):
                continue
            care_enabled = getattr(adult, "is_care_feature_enabled", None)
            if callable(care_enabled) and not bool(care_enabled()):
                continue
            sleeping_candidates.append(
                SleepingCaregiverCandidate(
                    name=self._pet_name(adult),
                    available=True,
                    distance_to_child=self._distance(adult, child),
                    shallow_sleeper=(
                        self._pet_name(adult) == SIRIUS_SYMBOLI_NAME
                    ),
                )
            )

        decision = choose_sleeping_caregiver_to_wake(
            sleeping_candidates,
            distressed_child_name=child_name,
            awake_or_responding_caregiver_available=awake_available,
        )
        if not decision.should_wake:
            return SleepRuntimeResult(False, decision.reason)
        caregiver = self._pets_by_name(adults).get(decision.caregiver_name)
        result = self.request_early_wake(
            caregiver,
            now=now,
            reason="child_distress",
            care_target_name=child_name,
        )
        if result.handled:
            caregiver.care_cooldown_end = min(
                float(getattr(caregiver, "care_cooldown_end", now) or now),
                now,
            )
        return result

    def _awake_caregiver_available(
        self,
        caregiver,
        child,
        *,
        now: float,
    ) -> bool:
        if self._sleep_activity_for_pet(caregiver) is not None:
            return False
        if not self._caregiver_in_range(caregiver, child):
            return False
        care_enabled = getattr(caregiver, "is_care_feature_enabled", None)
        if callable(care_enabled) and not bool(care_enabled()):
            return False
        is_under_care = getattr(caregiver, "is_under_care", None)
        is_offer_locked = getattr(caregiver, "is_offer_locked", None)
        return not bool(
            getattr(caregiver, "dragging", False)
            or getattr(caregiver, "is_angry_locked", False)
            or getattr(caregiver, "is_recovering", False)
            or getattr(caregiver, "care_partner", None) is not None
            or getattr(caregiver, "social_mode", "none") != "none"
            or getattr(caregiver, "flight_mode", "none") != "none"
            or getattr(caregiver, "perched_window_hwnd", 0)
            or getattr(caregiver, "offer_scene_kind", "none") != "none"
            or (
                callable(is_offer_locked)
                and bool(is_offer_locked(now))
            )
            or bool(str(getattr(caregiver, "held_item_kind", "") or ""))
            or getattr(caregiver, "intent_kind", "none")
            in SLEEP_JOIN_INTENT_KINDS
            or (
                callable(is_under_care)
                and bool(is_under_care(now))
            )
            or float(getattr(caregiver, "care_cooldown_end", 0.0) or 0.0)
            > now
            or self.coordinator.get_activity_for_participant(
                self._pet_name(caregiver)
            )
            is not None
        )

    def _caregiver_in_range(self, caregiver, child) -> bool:
        return bool(
            self._pet_name(caregiver) == SIRIUS_SYMBOLI_NAME
            or self._distance(caregiver, child) <= 1000.0
        )

    def interrupt_pet(
        self,
        pet,
        *,
        now: float,
        reason: str,
    ) -> SleepRuntimeResult:
        participant_name = self._pet_name(pet)
        activity = self.coordinator.get_activity_for_participant(
            participant_name
        )
        if activity is None:
            if participant_name in self.join_attempts:
                self._cancel_join_attempt(
                    participant_name,
                    pet=pet,
                    now=float(now),
                    retry=True,
                )
                return SleepRuntimeResult(
                    True,
                    reason,
                    participant_name=participant_name,
                    interrupted=True,
                )
            return SleepRuntimeResult(False, "activity_not_found")
        if activity.spec.kind != SLEEP_ACTIVITY_KIND:
            return SleepRuntimeResult(
                False,
                "unsupported_activity",
                activity_id=activity.activity_id,
                participant_name=participant_name,
            )
        return self._interrupt(
            activity.activity_id,
            pet=pet,
            now=float(now),
            reason=reason,
        )

    def interrupt_all(
        self,
        *,
        now: float,
        pets: Iterable[object],
        reason: str,
    ) -> tuple[SleepRuntimeResult, ...]:
        pets_by_name = self._pets_by_name(pets)
        for participant_name in tuple(self.join_attempts):
            self._cancel_join_attempt(
                participant_name,
                pet=pets_by_name.get(participant_name),
                now=float(now),
                retry=True,
            )
        results = []
        for activity in tuple(self.coordinator.get_active_activities()):
            if activity.spec.kind != SLEEP_ACTIVITY_KIND:
                continue
            participant_name = activity.participants[0].name
            results.append(
                self._interrupt(
                    activity.activity_id,
                    pet=pets_by_name.get(participant_name),
                    now=float(now),
                    reason=reason,
                )
            )
        return tuple(results)

    def _start_sleep(
        self,
        pet,
        *,
        now: float,
        world_mode: str,
        trigger_kind: str,
        group_id: str = "",
        anchor_name: str = "",
        group_slot: int = 0,
        target_activity_id: str = "",
    ) -> SleepRuntimeResult:
        participant_name = self._pet_name(pet)
        if not pet_form_allows_capability(
            pet,
            CAPABILITY_SLEEP,
        ):
            return SleepRuntimeResult(
                False,
                "form_blocks_sleep",
                participant_name=participant_name,
            )
        is_joined = trigger_kind == SLEEP_TRIGGER_OBSERVED_JOIN
        capability_evaluator = (
            evaluate_sleep_join_capability
            if is_joined
            else evaluate_sleep_capability
        )
        capability = capability_evaluator(
            getattr(pet, "asset_manager", None),
            mood_score=float(getattr(pet, "mood_score", 60.0)),
            resolver=self.runtime_adapter.animation_resolver,
            profile=self.profile,
        )
        snapshot = self.runtime_adapter.build_participant_snapshot(
            pet,
            role=self.profile.participant_role,
            now=now,
            capability_ready=capability.ready,
            capability_reason=(
                ""
                if capability.ready
                else f"{capability.phase_name}:{capability.reason}"
            ),
        )
        sleeping_seconds = self._sample(
            SLEEP_DURATION_MIN_SECONDS,
            SLEEP_DURATION_MAX_SECONDS,
        )
        start_result = self.coordinator.start(
            self.profile.build_activity_spec(sleeping_seconds),
            owner_name=participant_name,
            participant_snapshots=(snapshot,),
            now=now,
            source={
                SLEEP_TRIGGER_OBSERVED_JOIN: "sleep_observed_join",
                SLEEP_TRIGGER_SANDBOX_CONTROL: "sleep_sandbox_control",
            }.get(trigger_kind, "sleep_schedule"),
            metadata={
                "profile_key": self.profile.profile_key,
                "start_world_mode": str(world_mode or ""),
                "sleeping_seconds": sleeping_seconds,
                "sleep_trigger": trigger_kind,
                "sleep_group_id": str(group_id or ""),
                "sleep_anchor_name": str(anchor_name or ""),
                "sleep_group_slot": int(group_slot),
            },
        )
        if not start_result.started:
            return SleepRuntimeResult(
                False,
                start_result.reason,
                participant_name=participant_name,
            )

        self.runtime_adapter.apply_projections(
            {participant_name: pet},
            start_result.projections,
        )
        settling_binding = (
            self.profile.join_settling_animation
            if is_joined
            else self.profile.settling_animation
        )
        animation_result = self.runtime_adapter.apply_phase_animation(
            pet,
            settling_binding,
        )
        if not animation_result.applied:
            interrupted = self._interrupt(
                start_result.activity_id,
                pet=pet,
                now=now,
                reason="settling_animation_failed",
            )
            return SleepRuntimeResult(
                handled=interrupted.handled,
                reason=animation_result.reason,
                activity_id=start_result.activity_id,
                participant_name=participant_name,
                interrupted=interrupted.interrupted,
            )

        if is_joined:
            self._promote_sleep_group(
                group_id=group_id,
                anchor_name=anchor_name,
                target_activity_id=target_activity_id,
                joined_activity_id=start_result.activity_id,
                joined_slot=group_slot,
            )
        schedule = self.schedules.setdefault(
            participant_name,
            SleepScheduleState(awake_since=now),
        )
        schedule.next_proposal_at = 0.0
        schedule.next_social_probe_at = 0.0
        return SleepRuntimeResult(
            True,
            activity_id=start_result.activity_id,
            participant_name=participant_name,
            started=True,
            metadata=self._achievement_metadata(
                self.coordinator.get_activity(start_result.activity_id)
            ),
        )

    def _update_active(
        self,
        activity_id: str,
        *,
        now: float,
        world_mode: str,
        pet,
    ) -> SleepRuntimeResult:
        active = self.coordinator.get_activity(activity_id)
        if active is None or active.spec.kind != SLEEP_ACTIVITY_KIND:
            return SleepRuntimeResult(False, "activity_not_found")
        participant_name = active.participants[0].name
        group_id = str(active.metadata.get("sleep_group_id", "") or "")
        result_metadata = self._achievement_metadata(active)
        if pet is None:
            return self._interrupt(
                activity_id,
                pet=None,
                now=now,
                reason="participant_missing",
            )
        if str(active.metadata.get("start_world_mode", "")) != str(
            world_mode or ""
        ):
            return self._interrupt(
                activity_id,
                pet=pet,
                now=now,
                reason="world_mode_changed",
            )
        is_visible = getattr(pet, "isVisible", None)
        if (
            not bool(getattr(pet, "user_visible", True))
            or (callable(is_visible) and not bool(is_visible()))
        ):
            return self._interrupt(
                activity_id,
                pet=pet,
                now=now,
                reason="participant_hidden",
            )
        if bool(getattr(pet, "dragging", False)):
            return self._interrupt(
                activity_id,
                pet=pet,
                now=now,
                reason="participant_dragged",
            )

        transition = self.coordinator.update(activity_id, now=now)
        pets_by_name = {participant_name: pet}
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
        if transition.finished:
            self._schedule_after_wake(participant_name, now=now)
            if group_id:
                self._reanchor_sleep_group(group_id)
            return SleepRuntimeResult(
                True,
                activity_id=activity_id,
                participant_name=participant_name,
                finished=True,
                metadata=result_metadata,
            )

        phase_changed = any(
            event.event_name == "activity.phase_changed"
            for event in transition.events
        )
        if phase_changed:
            active = self.coordinator.get_activity(activity_id)
            binding = (
                self.profile.animation_for_phase(active.phase.name)
                if active is not None
                else None
            )
            if binding is None:
                return self._interrupt(
                    activity_id,
                    pet=pet,
                    now=now,
                    reason="phase_binding_missing",
                )
            animation_result = self.runtime_adapter.apply_phase_animation(
                pet,
                binding,
            )
            if not animation_result.applied:
                return self._interrupt(
                    activity_id,
                    pet=pet,
                    now=now,
                    reason="phase_animation_failed",
                )

        return SleepRuntimeResult(
            transition.handled,
            reason=transition.reason,
            activity_id=activity_id,
            participant_name=participant_name,
            phase_changed=phase_changed,
            metadata=result_metadata,
        )

    def _interrupt(
        self,
        activity_id: str,
        *,
        pet,
        now: float,
        reason: str,
    ) -> SleepRuntimeResult:
        active = self.coordinator.get_activity(activity_id)
        participant_name = (
            active.participants[0].name
            if active is not None and active.participants
            else self._pet_name(pet)
        )
        group_id = (
            str(active.metadata.get("sleep_group_id", "") or "")
            if active is not None
            else ""
        )
        result_metadata = self._achievement_metadata(active)
        transition = self.coordinator.interrupt(
            activity_id,
            now=now,
            reason=reason,
            force=True,
        )
        if transition.handled:
            if pet is not None:
                self.runtime_adapter.clear_released_participants(
                    {participant_name: pet},
                    transition.released_participant_names,
                    expected_activity_id=activity_id,
                )
            self._schedule_after_interrupt(participant_name, now=now)
            if group_id:
                self._reanchor_sleep_group(group_id)
        return SleepRuntimeResult(
            transition.handled,
            reason=reason,
            activity_id=activity_id,
            participant_name=participant_name,
            interrupted=transition.handled,
            metadata=result_metadata,
        )

    @staticmethod
    def _achievement_metadata(activity) -> dict[str, object]:
        if activity is None:
            return {}
        metadata = dict(getattr(activity, "metadata", {}) or {})
        metadata.update(
            {
                "source": str(getattr(activity, "source", "") or ""),
                "started_at": float(
                    getattr(activity, "started_at", 0.0) or 0.0
                ),
            }
        )
        return metadata

    def _start_due_sleep_observations(
        self,
        *,
        now: float,
        pets: tuple[object, ...],
        sleep_capacity: int,
    ):
        active_sleepers = tuple(
            activity
            for activity in self.coordinator.get_active_activities()
            if (
                activity.spec.kind == SLEEP_ACTIVITY_KIND
                and activity.phase.name == SLEEPING_PHASE
            )
        )
        if not active_sleepers:
            return
        pets_by_name = self._pets_by_name(pets)
        for observer in pets:
            observer_name = self._pet_name(observer)
            schedule = self.schedules.get(observer_name)
            if (
                not observer_name
                or not pet_form_allows_capability(
                    observer,
                    CAPABILITY_SLEEP,
                )
                or schedule is None
                or schedule.next_social_probe_at <= 0.0
                or now < schedule.next_social_probe_at
                or observer_name in self.join_attempts
                or self._sleep_activity_for_pet(observer) is not None
            ):
                continue
            schedule.next_social_probe_at = now + self._sample(
                SLEEP_SOCIAL_PROBE_MIN_SECONDS,
                SLEEP_SOCIAL_PROBE_MAX_SECONDS,
            )
            capability = evaluate_sleep_join_capability(
                getattr(observer, "asset_manager", None),
                mood_score=float(getattr(observer, "mood_score", 60.0)),
                resolver=self.runtime_adapter.animation_resolver,
                profile=self.profile,
            )
            if not capability.ready:
                self._schedule_social_retry(observer_name, now=now)
                continue
            observer_snapshot = self.runtime_adapter.build_participant_snapshot(
                observer,
                role=self.profile.participant_role,
                now=now,
            )
            candidates = []
            for target_activity in active_sleepers:
                target_name = target_activity.participants[0].name
                target_pet = pets_by_name.get(target_name)
                if target_pet is None or not self._pet_is_visible(target_pet):
                    continue
                distance = self._distance(observer, target_pet)
                group_size = self._sleep_group_size(target_activity)
                reserved = self._reserved_joiner_count(target_activity)
                decision = evaluate_sleep_join_candidate(
                    SleepJoinCandidateSnapshot(
                        observer_name=observer_name,
                        target_name=target_name,
                        distance=distance,
                        target_is_sleeping=True,
                        observer_busy=bool(
                            observer_snapshot.active_activity_id
                            or observer_snapshot.busy_reasons
                        ),
                        group_size=group_size,
                        reserved_joiners=reserved,
                        active_sleep_count=self._active_sleep_count(),
                        max_concurrent_sleepers=(
                            sleep_capacity
                        ),
                    )
                )
                if decision.allowed:
                    candidates.append((distance, target_activity, target_pet))
            if not candidates:
                continue
            _distance, target_activity, target_pet = min(
                candidates,
                key=lambda item: item[0],
            )
            duration = self._sample(
                SLEEP_OBSERVE_MIN_SECONDS,
                SLEEP_OBSERVE_MAX_SECONDS,
            )
            attempt = SleepJoinAttemptState(
                observer_name=observer_name,
                target_name=self._pet_name(target_pet),
                target_activity_id=target_activity.activity_id,
                phase=SLEEP_JOIN_PHASE_OBSERVING,
                phase_ends_at=now + duration,
                started_at=now,
            )
            self.join_attempts[observer_name] = attempt
            self._set_join_intent(observer, attempt, now=now)

    def _should_join_after_observing(
        self,
        observer,
        target_pet,
        target_activity,
        *,
        now: float,
    ) -> bool:
        observer_name = self._pet_name(observer)
        schedule = self.schedules.get(observer_name, SleepScheduleState())
        relationship = getattr(
            observer,
            "relationship_entries",
            {},
        ).get(self._pet_name(target_pet))
        decision = evaluate_sleep_join_influence(
            SleepJoinInfluenceSnapshot(
                awake_seconds=max(0.0, now - schedule.awake_since),
                autonomous_schedule_due=(
                    schedule.next_proposal_at > 0.0
                    and now >= schedule.next_proposal_at
                ),
                distance=self._distance(observer, target_pet),
                familiarity=float(
                    getattr(relationship, "familiarity", 0.0)
                ),
                attachment=float(
                    getattr(relationship, "attachment", 0.0)
                ),
                tension=float(getattr(relationship, "tension", 0.0)),
                group_size=self._sleep_group_size(target_activity),
            ),
            roll=self.random_value(),
        )
        return decision.should_join

    def _build_group_join_plan(self, target_activity):
        group_id = str(
            target_activity.metadata.get("sleep_group_id", "") or ""
        )
        members = self._sleep_group_members(target_activity)
        occupied_slots = [
            int(activity.metadata.get("sleep_group_slot", 0) or 0)
            for activity in members
        ]
        for attempt in self.join_attempts.values():
            if (
                attempt.phase == SLEEP_JOIN_PHASE_APPROACHING
                and attempt.slot
                and (
                    attempt.target_activity_id == target_activity.activity_id
                    or (group_id and attempt.group_id == group_id)
                )
            ):
                occupied_slots.append(int(attempt.slot))
        return build_sleep_group_join_plan(
            target_activity_id=target_activity.activity_id,
            target_name=target_activity.participants[0].name,
            existing_group_id=group_id,
            existing_anchor_name=str(
                target_activity.metadata.get("sleep_anchor_name", "") or ""
            ),
            occupied_slots=tuple(occupied_slots),
        )

    def _promote_sleep_group(
        self,
        *,
        group_id: str,
        anchor_name: str,
        target_activity_id: str,
        joined_activity_id: str,
        joined_slot: int,
    ):
        for activity in self.coordinator.get_active_activities():
            if activity.spec.kind != SLEEP_ACTIVITY_KIND:
                continue
            activity_group_id = str(
                activity.metadata.get("sleep_group_id", "") or ""
            )
            if (
                activity.activity_id == target_activity_id
                or activity.activity_id == joined_activity_id
                or activity_group_id == group_id
            ):
                activity.metadata["sleep_group_id"] = group_id
                activity.metadata["sleep_anchor_name"] = anchor_name
                if activity.activity_id == target_activity_id and not activity_group_id:
                    activity.metadata["sleep_group_slot"] = 0
                if activity.activity_id == joined_activity_id:
                    activity.metadata["sleep_group_slot"] = int(joined_slot)

    def _reanchor_sleep_group(self, group_id: str):
        members = [
            activity
            for activity in self.coordinator.get_active_activities()
            if (
                activity.spec.kind == SLEEP_ACTIVITY_KIND
                and str(
                    activity.metadata.get("sleep_group_id", "") or ""
                ) == group_id
            )
        ]
        if not members:
            return
        members.sort(key=lambda activity: activity.started_at)
        anchor_name = members[0].participants[0].name
        slots = [0]
        distance = 1
        while len(slots) < len(members):
            slots.extend((distance, -distance))
            distance += 1
        for index, activity in enumerate(members):
            activity.metadata["sleep_anchor_name"] = anchor_name
            activity.metadata["sleep_group_slot"] = slots[index]

    def _sleep_group_members(self, target_activity):
        group_id = str(
            target_activity.metadata.get("sleep_group_id", "") or ""
        )
        if not group_id:
            return (target_activity,)
        return tuple(
            activity
            for activity in self.coordinator.get_active_activities()
            if (
                activity.spec.kind == SLEEP_ACTIVITY_KIND
                and str(
                    activity.metadata.get("sleep_group_id", "") or ""
                ) == group_id
            )
        )

    def _sleep_group_size(self, target_activity) -> int:
        return len(self._sleep_group_members(target_activity))

    def _reserved_joiner_count(self, target_activity) -> int:
        target_group_id = str(
            target_activity.metadata.get("sleep_group_id", "") or ""
        )
        count = 0
        for attempt in self.join_attempts.values():
            attempt_target = self.coordinator.get_activity(
                attempt.target_activity_id
            )
            if attempt_target is None:
                continue
            attempt_group_id = str(
                attempt_target.metadata.get("sleep_group_id", "") or ""
            )
            if target_group_id:
                if attempt_group_id == target_group_id:
                    count += 1
            elif attempt.target_activity_id == target_activity.activity_id:
                count += 1
        return count

    def _prune_join_attempts(
        self,
        *,
        now: float,
        pets_by_name: dict[str, object],
    ):
        for participant_name in tuple(self.join_attempts):
            pet = pets_by_name.get(participant_name)
            if pet is None or not self._observer_can_continue(pet, now=now):
                self._cancel_join_attempt(
                    participant_name,
                    pet=pet,
                    now=now,
                    retry=True,
                )

    def _observer_can_continue(self, pet, *, now: float) -> bool:
        if pet is None or not self._pet_is_visible(pet):
            return False
        if not pet_form_allows_capability(
            pet,
            CAPABILITY_SLEEP,
        ):
            return False
        if bool(getattr(pet, "dragging", False)):
            return False
        if bool(getattr(pet, "is_angry_locked", False)):
            return False
        if bool(getattr(pet, "is_recovering", False)):
            return False
        if getattr(pet, "care_mode", "none") != "none":
            return False
        if getattr(pet, "care_partner", None) is not None:
            return False
        is_under_care = getattr(pet, "is_under_care", None)
        if callable(is_under_care) and bool(is_under_care(now)):
            return False
        if getattr(pet, "social_mode", "none") != "none":
            return False
        if getattr(pet, "flight_mode", "none") != "none":
            return False
        if bool(getattr(pet, "perched_window_hwnd", 0)):
            return False
        if float(getattr(pet, "vy", 0.0) or 0.0) != 0.0:
            return False
        if self._sleep_activity_for_pet(pet) is not None:
            return False
        return getattr(pet, "intent_kind", "none") in SLEEP_JOIN_INTENT_KINDS

    def _set_join_intent(
        self,
        pet,
        attempt: SleepJoinAttemptState,
        *,
        now: float,
    ):
        intent_kind = (
            INTENT_SLEEP_OBSERVE
            if attempt.phase == SLEEP_JOIN_PHASE_OBSERVING
            else INTENT_SLEEP_JOIN_APPROACH
        )
        pet.intent_kind = intent_kind
        pet.intent_target_name = attempt.target_name
        pet.intent_priority = 55
        pet.intent_source = "activity"
        pet.intent_context = attempt.phase
        pet.intent_reason = "sleeper_observed"
        pet.intent_locked_until = max(now, attempt.phase_ends_at)
        pet.intent_reconsider_after = 0.0

    def _clear_join_intent(self, pet, *, now: float):
        if pet is None or getattr(pet, "intent_kind", "none") not in (
            SLEEP_JOIN_INTENT_KINDS
        ):
            return
        pet.intent_kind = INTENT_AMBIENT_IDLE
        pet.intent_target_name = ""
        pet.intent_priority = 10
        pet.intent_source = "ambient"
        pet.intent_context = "ambient_idle"
        pet.intent_reason = "sleep_join_finished"
        pet.intent_locked_until = 0.0
        pet.intent_reconsider_after = float(now)

    def _cancel_join_attempt(
        self,
        participant_name: str,
        *,
        pet,
        now: float,
        retry: bool,
    ):
        self.join_attempts.pop(participant_name, None)
        self._clear_join_intent(pet, now=now)
        if retry and participant_name:
            self._schedule_social_retry(participant_name, now=now)

    def _resolve_join_target_x(self, pet, anchor_pet, *, slot: int) -> float:
        joiner_width = self._pet_width(pet)
        target_x = resolve_sleep_join_target_x(
            anchor_x=self._pet_x(anchor_pet),
            anchor_width=self._pet_width(anchor_pet),
            joiner_width=joiner_width,
            slot=slot,
        )
        clamp = getattr(pet, "clamp_x_to_virtual_geometry", None)
        if callable(clamp):
            target_x = clamp(target_x, joiner_width)
        return float(target_x)

    def _face_pet(self, pet, target_pet):
        if pet is not None and target_pet is not None:
            pet.direction = -1 if self._pet_x(target_pet) < self._pet_x(pet) else 1

    def _sleeping_activity_for_pet(self, pet):
        activity = self._sleep_activity_for_pet(pet)
        if activity is None or activity.phase.name != SLEEPING_PHASE:
            return None
        return activity

    def _sleep_activity_for_pet(self, pet):
        participant_name = self._pet_name(pet)
        if not participant_name:
            return None
        activity = self.coordinator.get_activity_for_participant(
            participant_name
        )
        if activity is None or activity.spec.kind != SLEEP_ACTIVITY_KIND:
            return None
        return activity

    def _active_sleep_count(self) -> int:
        return sum(
            activity.spec.kind == SLEEP_ACTIVITY_KIND
            for activity in self.coordinator.get_active_activities()
        )

    def _resolve_sleep_capacity(self, pets: Iterable[object]) -> int:
        if self.max_concurrent_sleepers is not None:
            return self.max_concurrent_sleepers
        return sum(self._pet_is_visible(pet) for pet in pets or ())

    def _ensure_schedule(self, participant_name: str, *, now: float):
        if participant_name in self.schedules:
            schedule = self.schedules[participant_name]
            if schedule.awake_since < 0.0:
                schedule.awake_since = now
            if (
                schedule.next_social_probe_at <= 0.0
                and schedule.next_proposal_at > 0.0
            ):
                schedule.next_social_probe_at = now + self._sample(
                    SLEEP_SOCIAL_PROBE_MIN_SECONDS,
                    SLEEP_SOCIAL_PROBE_MAX_SECONDS,
                )
            return
        self.schedules[participant_name] = SleepScheduleState(
            next_proposal_at=now
            + self._sample(
                SLEEP_INITIAL_DELAY_MIN_SECONDS,
                SLEEP_INITIAL_DELAY_MAX_SECONDS,
            ),
            awake_since=now,
            next_social_probe_at=now
            + self._sample(
                SLEEP_SOCIAL_PROBE_MIN_SECONDS,
                SLEEP_SOCIAL_PROBE_MAX_SECONDS,
            ),
        )

    def _is_due(self, pet, *, now: float) -> bool:
        participant_name = self._pet_name(pet)
        if not participant_name:
            return False
        schedule = self.schedules.get(participant_name)
        if schedule is None or schedule.next_proposal_at <= 0.0:
            return False
        return now >= schedule.next_proposal_at

    def _schedule_retry(self, participant_name: str, *, now: float):
        self.schedules[participant_name].next_proposal_at = (
            now
            + self._sample(
                SLEEP_RETRY_MIN_SECONDS,
                SLEEP_RETRY_MAX_SECONDS,
            )
        )

    def _schedule_social_retry(
        self,
        participant_name: str,
        *,
        now: float,
    ):
        schedule = self.schedules.setdefault(
            participant_name,
            SleepScheduleState(awake_since=now),
        )
        schedule.next_social_probe_at = now + self._sample(
            SLEEP_SOCIAL_RETRY_MIN_SECONDS,
            SLEEP_SOCIAL_RETRY_MAX_SECONDS,
        )

    def _schedule_after_wake(
        self,
        participant_name: str,
        *,
        now: float,
    ):
        schedule = self.schedules.setdefault(
            participant_name,
            SleepScheduleState(),
        )
        schedule.last_woke_at = now
        schedule.awake_since = now
        schedule.next_proposal_at = now + self._sample(
            SLEEP_COOLDOWN_MIN_SECONDS,
            SLEEP_COOLDOWN_MAX_SECONDS,
        )
        schedule.next_social_probe_at = now + self._sample(
            SLEEP_SOCIAL_PROBE_MIN_SECONDS,
            SLEEP_SOCIAL_PROBE_MAX_SECONDS,
        )

    def _schedule_after_interrupt(
        self,
        participant_name: str,
        *,
        now: float,
    ):
        if not participant_name:
            return
        schedule = self.schedules.setdefault(
            participant_name,
            SleepScheduleState(),
        )
        schedule.last_woke_at = now
        schedule.awake_since = now
        schedule.next_proposal_at = now + self._sample(
            SLEEP_INTERRUPTED_COOLDOWN_MIN_SECONDS,
            SLEEP_INTERRUPTED_COOLDOWN_MAX_SECONDS,
        )
        schedule.next_social_probe_at = now + self._sample(
            SLEEP_SOCIAL_PROBE_MIN_SECONDS,
            SLEEP_SOCIAL_PROBE_MAX_SECONDS,
        )

    def _sample(self, minimum: float, maximum: float) -> float:
        return max(
            float(minimum),
            min(float(maximum), float(self.uniform(minimum, maximum))),
        )

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
        getter = getattr(pet, "width", None)
        return max(
            1.0,
            float(
                getter()
                if callable(getter)
                else getattr(pet, "width", 100.0)
            ),
        )

    @classmethod
    def _distance(cls, pet, target_pet) -> float:
        distance_to = getattr(pet, "distance_to", None)
        if callable(distance_to):
            return float(distance_to(target_pet))
        return abs(cls._pet_x(pet) - cls._pet_x(target_pet))
