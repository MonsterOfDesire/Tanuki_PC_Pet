from __future__ import annotations

import math
import random
from itertools import combinations
from typing import Callable, Iterable

from .activity_coordinator import ActivityCoordinator
from .activity_runtime_adapter import ActivityRuntimeAdapter
from .geometry import get_total_virtual_geometry
from .race_profiles import (
    RACE_PROFILE,
    build_race_requirements,
    evaluate_race_capability,
    race_profile_supports_form,
)
from .race_rules import (
    RACE_ACTIVITY_KIND,
    RACE_ARRIVAL_DISTANCE,
    RACE_CHALLENGE_PHASE,
    RACE_FINISH_MAX_SEPARATION,
    RACE_FINISH_PHASE,
    RACE_FINISH_STANDOFF_DISTANCE,
    RACE_OPPONENT_ROLE,
    RACE_POST_INTERACTION_SECONDS,
    RACE_READY_PHASE,
    RACE_RECOVERY_PHASE,
    RACE_RESPONSE_PHASE,
    RACE_RUNNING_SPEED_SCALE,
    RACE_RUNNING_PHASE,
    RACE_TO_START_PHASE,
    RACE_TO_START_SPEED_SCALE,
    RACE_TO_START_STALL_REPLAN_SECONDS,
    RACE_CHALLENGER_ROLE,
    RaceEmergencySnapshot,
    RaceEligibilitySnapshot,
    build_race_lane_geometry,
    decide_race_acceptance,
    decide_race_performance,
    evaluate_race_eligibility,
    evaluate_race_emergency_interrupt,
    get_race_expected_speed,
    get_race_schedule_policy,
    race_finish_is_ready,
    race_pair_spacing_reason,
    resolve_race_finish_band,
)
from .race_state import (
    RACE_EXECUTION_AUTONOMOUS,
    RACE_EXECUTION_NORMAL,
    RACE_EXECUTION_SANDBOX_PREVIEW,
    RaceEvent,
    RacePlan,
    RaceRuntimeResult,
    RaceScheduleState,
)
from .transformation_profiles import (
    CAPABILITY_RACE,
    get_pet_form_key,
    pet_form_allows_capability,
)


class RaceExecutor:
    def __init__(
        self,
        *,
        coordinator: ActivityCoordinator,
        runtime_adapter: ActivityRuntimeAdapter,
        schedule: RaceScheduleState | None = None,
        uniform: Callable[[float, float], float] | None = None,
        random_value: Callable[[], float] | None = None,
        bounds_provider: Callable[[tuple[object, ...]], tuple[float, float]] | None = None,
        frequency_provider: Callable[[], str] | None = None,
    ):
        self.coordinator = coordinator
        self.runtime_adapter = runtime_adapter
        self.schedule = schedule or RaceScheduleState()
        self.uniform = uniform or random.uniform
        self.random_value = random_value or random.random
        self.bounds_provider = bounds_provider or self._default_bounds
        self.frequency_provider = frequency_provider or (lambda: "normal")

    def _frequency_key(self) -> str:
        value = str(self.frequency_provider() or "normal")
        return value if value in {"frequent", "normal", "occasional"} else "normal"

    def is_preview_active(self) -> bool:
        activity = self._active_race()
        return bool(
            activity is not None
            and str(activity.metadata.get("execution_mode", ""))
            == RACE_EXECUTION_SANDBOX_PREVIEW
        )

    def update(
        self,
        *,
        now: float,
        world_mode: str,
        pets: Iterable[object],
        record_race_event=None,
    ) -> RaceRuntimeResult:
        now = float(now)
        pets = tuple(pets or ())
        active = self._active_race()
        if active is not None:
            return self._update_active(
                active.activity_id,
                now=now,
                world_mode=world_mode,
                pets=pets,
                record_race_event=record_race_event,
            )
        world_mode = str(world_mode or "")
        frequency_key = self._frequency_key()
        policy = get_race_schedule_policy(world_mode, frequency_key)
        if policy is None:
            return RaceRuntimeResult(False, "world_mode_disabled")
        if self.schedule.world_mode and self.schedule.world_mode != world_mode:
            self.schedule.world_mode = world_mode
            self.schedule.next_proposal_at = 0.0
        elif not self.schedule.world_mode:
            self.schedule.world_mode = world_mode
        if (
            self.schedule.frequency_key
            and self.schedule.frequency_key != frequency_key
        ):
            self.schedule.next_proposal_at = 0.0
        self.schedule.frequency_key = frequency_key
        if self.schedule.next_proposal_at <= 0.0:
            self.schedule.next_proposal_at = now + self._sample(
                policy.initial_min_seconds,
                policy.initial_max_seconds,
            )
            self.schedule.last_wait_reason = "cooldown"
            return RaceRuntimeResult(False, "schedule_initialized")
        if now < self.schedule.next_proposal_at:
            self.schedule.last_wait_reason = "cooldown"
            return RaceRuntimeResult(False, "schedule_not_due")

        plan_or_reason = self._build_autonomous_plan(
            pets,
            now=now,
            world_mode=world_mode,
        )
        if not isinstance(plan_or_reason, RacePlan):
            self.schedule.last_wait_reason = str(plan_or_reason or "no_pair")
            self._schedule_retry(now, world_mode=world_mode)
            return RaceRuntimeResult(False, str(plan_or_reason or "no_pair"))
        result = self._start_plan(plan_or_reason, pets=pets, now=now)
        if not result.started:
            self.schedule.last_wait_reason = str(result.reason or "start_failed")
            self._schedule_retry(now, world_mode=world_mode)
        else:
            self.schedule.last_wait_reason = ""
        return result

    def start_preview(
        self,
        *,
        now: float,
        world_mode: str,
        rudolf_pet,
        teio_pet,
    ) -> RaceRuntimeResult:
        now = float(now)
        if str(world_mode or "") != "sandbox":
            return RaceRuntimeResult(False, "preview_requires_sandbox")
        if self._active_race() is not None:
            return RaceRuntimeResult(False, "race_already_active")
        if rudolf_pet is None or teio_pet is None:
            return RaceRuntimeResult(False, "participant_unavailable")
        pets = (rudolf_pet, teio_pet)
        for pet in pets:
            decision = self._eligibility_decision(
                pet,
                now=now,
                world_mode=world_mode,
                preview=True,
            )
            if not decision.allowed:
                return RaceRuntimeResult(
                    False,
                    f"{self._pet_name(pet)}:{decision.reason}",
                )
        spacing_reason = self._pair_spacing_reason(rudolf_pet, teio_pet)
        if spacing_reason:
            return RaceRuntimeResult(False, spacing_reason)
        performance = self._performance_decision(rudolf_pet, teio_pet)
        plan = RacePlan(
            challenger_name=self._pet_name(rudolf_pet),
            opponent_name=self._pet_name(teio_pet),
            accepted=True,
            winner_name=performance.winner_name,
            challenger_speed=performance.challenger_speed,
            opponent_speed=performance.opponent_speed,
            execution_mode=RACE_EXECUTION_SANDBOX_PREVIEW,
            source="settings_preview",
            world_mode="sandbox",
        )
        return self._start_plan(plan, pets=pets, now=now)

    def interrupt_pet(
        self,
        pet,
        *,
        now: float,
        reason: str,
        pets: Iterable[object] = (),
    ) -> RaceRuntimeResult:
        activity = self.coordinator.get_activity_for_participant(
            self._pet_name(pet)
        )
        if activity is None or activity.spec.kind != RACE_ACTIVITY_KIND:
            return RaceRuntimeResult(False, "race_not_found")
        return self._interrupt(
            activity.activity_id,
            now=float(now),
            reason=reason,
            pets=tuple(pets or (pet,)),
        )

    def interrupt_active(
        self,
        *,
        now: float,
        pets: Iterable[object],
        reason: str,
    ) -> RaceRuntimeResult:
        activity = self._active_race()
        if activity is None:
            return RaceRuntimeResult(False, "race_not_found")
        return self._interrupt(
            activity.activity_id,
            now=float(now),
            reason=reason,
            pets=tuple(pets or ()),
        )

    def _build_autonomous_plan(self, pets, *, now: float, world_mode: str):
        eligible = []
        for pet in pets:
            decision = self._eligibility_decision(
                pet,
                now=now,
                world_mode=world_mode,
                preview=False,
            )
            if decision.allowed:
                eligible.append(pet)
        candidate_pairs = tuple(combinations(eligible, 2))
        if not candidate_pairs:
            return "not_enough_eligible_participants"
        pair_reasons = tuple(
            (pair, self._pair_spacing_reason(*pair))
            for pair in candidate_pairs
        )
        pairs = tuple(pair for pair, reason in pair_reasons if not reason)
        if not pairs:
            reasons = {reason for _pair, reason in pair_reasons}
            if reasons == {"participants_too_close"}:
                return "participants_too_close"
            return "participants_too_far"
        pair = pairs[self._roll_index(len(pairs))]
        if self.random_value() < 0.5:
            challenger, opponent = pair
        else:
            opponent, challenger = pair
        acceptance = decide_race_acceptance(
            opponent_name=self._pet_name(opponent),
            opponent_form=get_pet_form_key(opponent),
            mood_score=float(getattr(opponent, "mood_score", 60.0)),
            roll=self.random_value(),
        )
        performance = (
            self._performance_decision(challenger, opponent)
            if acceptance.accepted
            else None
        )
        return RacePlan(
            challenger_name=self._pet_name(challenger),
            opponent_name=self._pet_name(opponent),
            accepted=acceptance.accepted,
            winner_name=(performance.winner_name if performance else ""),
            challenger_speed=(
                performance.challenger_speed if performance else 0.0
            ),
            opponent_speed=(
                performance.opponent_speed if performance else 0.0
            ),
            execution_mode=RACE_EXECUTION_NORMAL,
            source="autonomous",
            world_mode=str(world_mode or ""),
        )

    def _start_plan(self, plan: RacePlan, *, pets, now: float) -> RaceRuntimeResult:
        pets_by_name = self._pets_by_name(pets)
        challenger = pets_by_name.get(plan.challenger_name)
        opponent = pets_by_name.get(plan.opponent_name)
        if challenger is None or opponent is None:
            return RaceRuntimeResult(False, "participant_unavailable")
        spacing_reason = self._pair_spacing_reason(challenger, opponent)
        if spacing_reason:
            return RaceRuntimeResult(False, spacing_reason)
        capability_snapshots = []
        for pet, role, other in (
            (challenger, RACE_CHALLENGER_ROLE, opponent),
            (opponent, RACE_OPPONENT_ROLE, challenger),
        ):
            requirements = build_race_requirements(
                character_name=self._pet_name(pet),
                opponent_name=self._pet_name(other),
                opponent_form=get_pet_form_key(other),
                role=role,
                accepted=plan.accepted,
                winner=None if plan.accepted else False,
                transformed=get_pet_form_key(pet) == "transformed",
            )
            capability = evaluate_race_capability(
                getattr(pet, "asset_manager", None),
                mood_score=float(getattr(pet, "mood_score", 60.0)),
                requirements=requirements,
                resolver=self.runtime_adapter.animation_resolver,
            )
            capability_snapshots.append(
                self.runtime_adapter.build_participant_snapshot(
                    pet,
                    role=role,
                    now=now,
                    capability_ready=capability.ready,
                    capability_reason=(
                        ""
                        if capability.ready
                        else f"{capability.phase_name}:{capability.reason}"
                    ),
                )
            )

        left_bound, right_bound = self.bounds_provider((challenger, opponent))
        lane = build_race_lane_geometry(
            left_bound=left_bound,
            right_bound=right_bound,
            participant_widths=(
                self._pet_width(challenger),
                self._pet_width(opponent),
            ),
            participant_radii=(
                self._pet_radius(challenger),
                self._pet_radius(opponent),
            ),
            participant_positions=(
                self._pet_x(challenger),
                self._pet_x(opponent),
            ),
        )
        challenger_start_x = lane.challenger_start_x
        opponent_start_x = lane.opponent_start_x
        challenger_speed = float(plan.challenger_speed or 0.0)
        opponent_speed = float(plan.opponent_speed or 0.0)
        if plan.accepted and challenger_speed <= 0.0:
            challenger_speed = get_race_expected_speed(
                character_name=self._pet_name(challenger),
                form_key=get_pet_form_key(challenger),
                mood_score=float(getattr(challenger, "mood_score", 60.0)),
            )
        if plan.accepted and opponent_speed <= 0.0:
            opponent_speed = get_race_expected_speed(
                character_name=self._pet_name(opponent),
                form_key=get_pet_form_key(opponent),
                mood_score=float(getattr(opponent, "mood_score", 60.0)),
            )
        start_result = self.coordinator.start(
            RACE_PROFILE.activity_spec,
            owner_name=plan.challenger_name,
            participant_snapshots=tuple(capability_snapshots),
            now=now,
            source=plan.source,
            metadata={
                "profile_key": RACE_PROFILE.profile_key,
                "execution_mode": plan.execution_mode,
                "challenger_name": plan.challenger_name,
                "opponent_name": plan.opponent_name,
                "accepted": plan.accepted,
                "predicted_winner_name": plan.winner_name,
                "winner_name": "",
                "loser_name": "",
                "challenger_form": get_pet_form_key(challenger),
                "opponent_form": get_pet_form_key(opponent),
                "challenger_start_x": challenger_start_x,
                "opponent_start_x": opponent_start_x,
                "finish_x": lane.finish_x,
                "challenger_finish_x": (
                    challenger_start_x + (lane.direction * lane.distance)
                ),
                "opponent_finish_x": (
                    opponent_start_x + (lane.direction * lane.distance)
                ),
                "race_direction": lane.direction,
                "race_distance": lane.distance,
                "challenger_speed": challenger_speed,
                "opponent_speed": opponent_speed,
                "world_mode": plan.world_mode,
                "running_started_at": 0.0,
                "winner_arrived_at": 0.0,
                "race_elapsed_seconds": 0.0,
                "challenger_move_remainder": 0.0,
                "opponent_move_remainder": 0.0,
                "to_start_last_progress_at": float(now),
                "to_start_last_distance": 0.0,
            },
        )
        if not start_result.started:
            return RaceRuntimeResult(False, start_result.reason)
        self.runtime_adapter.apply_projections(
            pets_by_name,
            start_result.projections,
        )
        self._face_each_other(challenger, opponent)
        animation_result = self.runtime_adapter.apply_phase_animation(
            challenger,
            RACE_PROFILE.challenge_animation,
        )
        if not animation_result.applied:
            return self._interrupt(
                start_result.activity_id,
                now=now,
                reason="challenge_animation_failed",
                pets=(challenger, opponent),
            )
        consider_result = self.runtime_adapter.apply_phase_animation(
            opponent,
            RACE_PROFILE.consider_animation,
        )
        if not consider_result.applied:
            return self._interrupt(
                start_result.activity_id,
                now=now,
                reason="consider_animation_failed",
                pets=(challenger, opponent),
            )
        return RaceRuntimeResult(
            True,
            activity_id=start_result.activity_id,
            started=True,
            accepted=plan.accepted,
            winner_name="",
        )

    def _update_active(
        self,
        activity_id: str,
        *,
        now: float,
        world_mode: str,
        pets,
        record_race_event,
    ) -> RaceRuntimeResult:
        activity = self.coordinator.get_activity(activity_id)
        if activity is None:
            return RaceRuntimeResult(False, "race_not_found")
        expected_mode = str(
            activity.metadata.get("world_mode", "golden_legend")
            or "golden_legend"
        )
        if str(world_mode or "") != expected_mode:
            return self._interrupt(
                activity_id,
                now=now,
                reason="world_mode_changed",
                pets=pets,
            )
        emergency = self._emergency_decision(pets)
        if emergency.should_interrupt:
            return self._interrupt(
                activity_id,
                now=now,
                reason=emergency.reason,
                pets=pets,
            )
        pets_by_name = self._pets_by_name(pets)
        participant_pets = tuple(
            pets_by_name.get(participant.name)
            for participant in activity.participants
        )
        if any(pet is None for pet in participant_pets):
            return self._interrupt(
                activity_id,
                now=now,
                reason="participant_missing",
                pets=pets,
            )
        for pet in participant_pets:
            if not self._pet_is_visible(pet):
                return self._interrupt(
                    activity_id,
                    now=now,
                    reason="participant_hidden",
                    pets=pets,
                )

        phase = activity.phase.name
        if phase == RACE_CHALLENGE_PHASE:
            if now >= activity.phase_ends_at:
                return self._advance_phase(
                    activity_id,
                    RACE_RESPONSE_PHASE,
                    now=activity.phase_ends_at,
                    pets_by_name=pets_by_name,
                )
        elif phase == RACE_RESPONSE_PHASE:
            if now >= activity.phase_ends_at:
                if not bool(activity.metadata.get("accepted", False)):
                    return self._complete_declined(
                        activity,
                        now=activity.phase_ends_at,
                        pets_by_name=pets_by_name,
                        record_race_event=record_race_event,
                    )
                return self._advance_phase(
                    activity_id,
                    RACE_TO_START_PHASE,
                    now=activity.phase_ends_at,
                    pets_by_name=pets_by_name,
                )
        elif phase == RACE_TO_START_PHASE:
            arrived = self._move_to_start(
                activity,
                pets_by_name,
                now=now,
            )
            if arrived:
                return self._advance_phase(
                    activity_id,
                    RACE_READY_PHASE,
                    now=now,
                    pets_by_name=pets_by_name,
                )
        elif phase == RACE_READY_PHASE:
            if now >= activity.phase_ends_at:
                return self._advance_phase(
                    activity_id,
                    RACE_RUNNING_PHASE,
                    now=activity.phase_ends_at,
                    pets_by_name=pets_by_name,
                )
        elif phase == RACE_RUNNING_PHASE:
            finish_ready, animation_failure = self._move_running(
                activity,
                pets_by_name,
                now=now,
            )
            if animation_failure:
                return self._interrupt(
                    activity_id,
                    now=now,
                    reason=f"winner_animation_failed:{animation_failure}",
                    pets=pets,
                )
            if finish_ready:
                if not activity.result_committed:
                    self.coordinator.commit_result(
                        activity_id,
                        now=now,
                        result={
                            "outcome": "completed",
                            "accepted": True,
                            "winner_name": str(
                                activity.metadata.get("winner_name", "")
                            ),
                            "loser_name": str(
                                activity.metadata.get("loser_name", "")
                            ),
                        },
                    )
                return self._advance_phase(
                    activity_id,
                    RACE_FINISH_PHASE,
                    now=now,
                    pets_by_name=pets_by_name,
                )
            if now >= activity.phase_ends_at:
                return self._interrupt(
                    activity_id,
                    now=now,
                    reason="running_timeout",
                    pets=pets,
                )
        elif phase == RACE_FINISH_PHASE:
            if now >= activity.phase_ends_at:
                return self._advance_phase(
                    activity_id,
                    RACE_RECOVERY_PHASE,
                    now=activity.phase_ends_at,
                    pets_by_name=pets_by_name,
                )
        elif phase == RACE_RECOVERY_PHASE and now >= activity.phase_ends_at:
            return self._complete_accepted(
                activity,
                now=activity.phase_ends_at,
                pets_by_name=pets_by_name,
                record_race_event=record_race_event,
            )
        return RaceRuntimeResult(
            True,
            activity_id=activity_id,
            accepted=bool(activity.metadata.get("accepted", False)),
            winner_name=str(activity.metadata.get("winner_name", "")),
        )

    def _advance_phase(self, activity_id, phase_name, *, now, pets_by_name):
        transition = self.coordinator.transition_to_phase(
            activity_id,
            phase_name=phase_name,
            now=float(now),
            reason="race_phase_ready",
        )
        self.runtime_adapter.apply_projections(
            pets_by_name,
            transition.projections,
        )
        activity = self.coordinator.get_activity(activity_id)
        if activity is None:
            return RaceRuntimeResult(False, "race_not_found")
        if phase_name == RACE_TO_START_PHASE:
            activity.metadata["to_start_last_progress_at"] = float(now)
            activity.metadata["to_start_last_distance"] = 0.0
        elif phase_name == RACE_RUNNING_PHASE:
            activity.metadata["running_started_at"] = float(now)
            activity.metadata["winner_arrived_at"] = 0.0
            activity.metadata["race_elapsed_seconds"] = 0.0
            activity.metadata["challenger_move_remainder"] = 0.0
            activity.metadata["opponent_move_remainder"] = 0.0
        self._apply_phase_facing(activity, pets_by_name)
        animation_failure = self._apply_phase_animations(
            activity,
            pets_by_name,
        )
        if animation_failure:
            return self._interrupt(
                activity_id,
                now=now,
                reason=f"{phase_name}_animation_failed:{animation_failure}",
                pets=tuple(pets_by_name.values()),
            )
        return RaceRuntimeResult(
            transition.handled,
            reason=transition.reason,
            activity_id=activity_id,
            phase_changed=transition.handled,
            accepted=bool(activity.metadata.get("accepted", False)),
            winner_name=str(activity.metadata.get("winner_name", "")),
        )

    def _apply_phase_animations(self, activity, pets_by_name) -> str:
        phase = activity.phase.name
        challenger_name = str(activity.metadata.get("challenger_name", ""))
        opponent_name = str(activity.metadata.get("opponent_name", ""))
        challenger = pets_by_name.get(challenger_name)
        opponent = pets_by_name.get(opponent_name)
        if phase == RACE_RESPONSE_PHASE:
            targets = (
                (
                    opponent,
                    RACE_PROFILE.response_animation(
                        bool(activity.metadata.get("accepted", False))
                    ),
                    "",
                ),
            )
        elif phase in {
            RACE_TO_START_PHASE,
            RACE_READY_PHASE,
            RACE_RUNNING_PHASE,
            RACE_FINISH_PHASE,
            RACE_RECOVERY_PHASE,
        }:
            targets = []
            for pet, other_name, form_key in (
                (
                    challenger,
                    opponent_name,
                    str(activity.metadata.get("challenger_form", "base")),
                ),
                (
                    opponent,
                    challenger_name,
                    str(activity.metadata.get("opponent_form", "base")),
                ),
            ):
                if phase == RACE_TO_START_PHASE:
                    binding, band_override = RACE_PROFILE.to_start_animation, ""
                elif phase == RACE_READY_PHASE:
                    binding, band_override = RACE_PROFILE.ready_animation, ""
                elif phase == RACE_RUNNING_PHASE:
                    other_form = (
                        str(activity.metadata.get("opponent_form", "base"))
                        if pet is challenger
                        else str(activity.metadata.get("challenger_form", "base"))
                    )
                    binding = RACE_PROFILE.running_animation_for(
                        self._pet_name(pet),
                        other_name,
                        opponent_form=other_form,
                    )
                    band_override = ""
                elif phase == RACE_FINISH_PHASE:
                    winner = self._pet_name(pet) == str(
                        activity.metadata.get("winner_name", "")
                    )
                    if winner and bool(
                        activity.metadata.get("winner_arrived", False)
                    ):
                        continue
                    binding = (
                        RACE_PROFILE.finish_win_animation
                        if winner
                        else RACE_PROFILE.finish_lose_animation
                    )
                    band_override = resolve_race_finish_band(
                        character_name=self._pet_name(pet),
                        opponent_name=other_name,
                        winner=winner,
                        transformed=form_key == "transformed",
                    )
                else:
                    binding, band_override = RACE_PROFILE.recovery_animation, ""
                targets.append((pet, binding, band_override))
            targets = tuple(targets)
        else:
            return ""
        for pet, binding, band_override in targets:
            if pet is None:
                return "participant_missing"
            result = self.runtime_adapter.apply_phase_animation(
                pet,
                binding,
                band_override=band_override,
            )
            if not result.applied:
                return self._pet_name(pet) or result.reason
        return ""

    def _move_to_start(self, activity, pets_by_name, *, now: float) -> bool:
        challenger = pets_by_name.get(
            str(activity.metadata.get("challenger_name", ""))
        )
        opponent = pets_by_name.get(
            str(activity.metadata.get("opponent_name", ""))
        )
        targets = (
            self._clamp_target_for_pet(
                challenger,
                float(activity.metadata.get("challenger_start_x", 0.0)),
            ),
            self._clamp_target_for_pet(
                opponent,
                float(activity.metadata.get("opponent_start_x", 0.0)),
            ),
        )
        activity.metadata["challenger_start_x"] = targets[0]
        activity.metadata["opponent_start_x"] = targets[1]
        total_distance_before = (
            abs(self._pet_x(challenger) - targets[0])
            + abs(self._pet_x(opponent) - targets[1])
        )
        arrivals = (
            self._move_pet(
                challenger,
                targets[0],
                speed_scale=RACE_TO_START_SPEED_SCALE,
            ),
            self._move_pet(
                opponent,
                targets[1],
                speed_scale=RACE_TO_START_SPEED_SCALE,
            ),
        )
        total_distance_after = (
            abs(self._pet_x(challenger) - targets[0])
            + abs(self._pet_x(opponent) - targets[1])
        )
        previous_distance = float(
            activity.metadata.get("to_start_last_distance", 0.0) or 0.0
        )
        if (
            previous_distance <= 0.0
            or total_distance_after < previous_distance - 0.5
            or total_distance_after < total_distance_before - 0.5
        ):
            activity.metadata["to_start_last_progress_at"] = float(now)
            activity.metadata["to_start_last_distance"] = total_distance_after
        elif (
            float(now)
            - float(activity.metadata.get("to_start_last_progress_at", now))
            >= RACE_TO_START_STALL_REPLAN_SECONDS
        ):
            self._replan_lane(activity, challenger, opponent, now=float(now))
        return all(arrivals)

    def _move_running(
        self,
        activity,
        pets_by_name,
        *,
        now: float,
    ) -> tuple[bool, str]:
        winner_name = str(activity.metadata.get("winner_name", ""))
        loser_name = str(activity.metadata.get("loser_name", ""))
        challenger_name = str(activity.metadata.get("challenger_name", ""))
        opponent_name = str(activity.metadata.get("opponent_name", ""))
        if not winner_name:
            arrivals = {}
            for role, participant_name in (
                ("challenger", challenger_name),
                ("opponent", opponent_name),
            ):
                pet = pets_by_name.get(participant_name)
                arrivals[participant_name] = self._move_pet_precise(
                    activity,
                    pet,
                    float(activity.metadata.get(f"{role}_finish_x", 0.0)),
                    speed=float(activity.metadata.get(f"{role}_speed", 1.0)),
                    remainder_key=f"{role}_move_remainder",
                )
            arrived_names = tuple(
                name for name, arrived in arrivals.items() if arrived
            )
            if arrived_names:
                predicted = str(
                    activity.metadata.get("predicted_winner_name", "")
                )
                winner_name = (
                    arrived_names[0]
                    if len(arrived_names) == 1 or predicted not in arrived_names
                    else predicted
                )
                loser_name = (
                    opponent_name
                    if winner_name == challenger_name
                    else challenger_name
                )
                activity.metadata["winner_name"] = winner_name
                activity.metadata["loser_name"] = loser_name
                activity.metadata["winner_arrived"] = True
                activity.metadata["winner_arrived_at"] = float(now)
                activity.metadata["race_elapsed_seconds"] = max(
                    0.0,
                    float(now)
                    - float(activity.metadata.get("running_started_at", now)),
                )
                winner = pets_by_name.get(winner_name)
                result = self.runtime_adapter.apply_phase_animation(
                    winner,
                    RACE_PROFILE.finish_win_animation,
                    band_override="normal",
                )
                if not result.applied:
                    return False, self._pet_name(winner) or result.reason

        if not winner_name:
            return False, ""

        winner = pets_by_name.get(winner_name)
        loser = pets_by_name.get(loser_name)
        separation = abs(self._pet_x(winner) - self._pet_x(loser))
        if separation > RACE_FINISH_MAX_SEPARATION:
            direction = int(activity.metadata.get("race_direction", 1) or 1)
            loser_target_x = self._pet_x(winner) - (
                direction * RACE_FINISH_STANDOFF_DISTANCE
            )
            loser_role = (
                "challenger" if loser_name == challenger_name else "opponent"
            )
            self._move_pet_precise(
                activity,
                loser,
                loser_target_x,
                speed=float(
                    activity.metadata.get(f"{loser_role}_speed", 1.0)
                ),
                remainder_key=f"{loser_role}_move_remainder",
            )
            self._face_each_other(winner, loser)

        separation = abs(self._pet_x(winner) - self._pet_x(loser))
        self._face_each_other(winner, loser)
        return race_finish_is_ready(
            winner_arrived=True,
            separation=separation,
        ), ""

    def _complete_declined(
        self,
        activity,
        *,
        now,
        pets_by_name,
        record_race_event,
    ):
        self.coordinator.commit_result(
            activity.activity_id,
            now=now,
            result={"outcome": "declined", "accepted": False},
        )
        transition = self.coordinator.finish(
            activity.activity_id,
            now=now,
            reason="challenge_declined",
        )
        self.runtime_adapter.clear_released_participants(
            pets_by_name,
            transition.released_participant_names,
            expected_activity_id=activity.activity_id,
        )
        self._record_event(
            activity,
            event_type="race_declined",
            occurred_at=now,
            record_race_event=record_race_event,
        )
        self._schedule_after_finish(activity, now)
        return RaceRuntimeResult(
            True,
            reason="challenge_declined",
            activity_id=activity.activity_id,
            finished=True,
            accepted=False,
        )

    def _complete_accepted(
        self,
        activity,
        *,
        now,
        pets_by_name,
        record_race_event,
    ):
        transition = self.coordinator.finish(
            activity.activity_id,
            now=now,
            reason="race_completed",
        )
        self.runtime_adapter.clear_released_participants(
            pets_by_name,
            transition.released_participant_names,
            expected_activity_id=activity.activity_id,
        )
        self._prime_post_race_interaction(
            activity,
            pets_by_name,
            now=float(now),
        )
        self._record_event(
            activity,
            event_type="race_completed",
            occurred_at=now,
            record_race_event=record_race_event,
        )
        self._schedule_after_finish(activity, now)
        return RaceRuntimeResult(
            True,
            reason="race_completed",
            activity_id=activity.activity_id,
            finished=True,
            accepted=True,
            winner_name=str(activity.metadata.get("winner_name", "")),
        )

    def _record_event(self, activity, *, event_type, occurred_at, record_race_event):
        if (
            str(activity.metadata.get("execution_mode", ""))
            == RACE_EXECUTION_SANDBOX_PREVIEW
            or not callable(record_race_event)
        ):
            return
        record_race_event(
            RaceEvent(
                event_type=event_type,
                occurred_at=float(occurred_at),
                challenger_name=str(
                    activity.metadata.get("challenger_name", "")
                ),
                opponent_name=str(
                    activity.metadata.get("opponent_name", "")
                ),
                winner_name=str(activity.metadata.get("winner_name", "")),
                loser_name=str(activity.metadata.get("loser_name", "")),
                source=activity.source,
                activity_id=activity.activity_id,
                challenger_form=str(
                    activity.metadata.get("challenger_form", "base")
                ),
                opponent_form=str(
                    activity.metadata.get("opponent_form", "base")
                ),
                execution_mode=str(
                    activity.metadata.get(
                        "execution_mode",
                        RACE_EXECUTION_AUTONOMOUS,
                    )
                ),
                world_mode=str(
                    activity.metadata.get("world_mode", "golden_legend")
                ),
                race_distance=float(
                    activity.metadata.get("race_distance", 0.0) or 0.0
                ),
                race_direction=int(
                    activity.metadata.get("race_direction", 1) or 1
                ),
                running_started_at=float(
                    activity.metadata.get("running_started_at", 0.0) or 0.0
                ),
                winner_arrived_at=float(
                    activity.metadata.get("winner_arrived_at", 0.0) or 0.0
                ),
                race_elapsed_seconds=float(
                    activity.metadata.get("race_elapsed_seconds", 0.0) or 0.0
                ),
            )
        )

    def _schedule_after_finish(self, activity, now):
        if str(activity.metadata.get("execution_mode", "")) == RACE_EXECUTION_SANDBOX_PREVIEW:
            return
        world_mode = str(
            activity.metadata.get("world_mode", "golden_legend")
            or "golden_legend"
        )
        frequency_key = self._frequency_key()
        policy = get_race_schedule_policy(world_mode, frequency_key)
        if policy is None:
            return
        self.schedule.world_mode = world_mode
        self.schedule.frequency_key = frequency_key
        self.schedule.last_wait_reason = "cooldown"
        self.schedule.last_finished_at = float(now)
        self.schedule.next_proposal_at = float(now) + self._sample(
            policy.cooldown_min_seconds,
            policy.cooldown_max_seconds,
        )

    def _schedule_retry(self, now, *, world_mode: str):
        frequency_key = self._frequency_key()
        policy = get_race_schedule_policy(world_mode, frequency_key)
        if policy is None:
            return
        self.schedule.world_mode = str(world_mode or "")
        self.schedule.frequency_key = frequency_key
        self.schedule.next_proposal_at = float(now) + self._sample(
            policy.retry_min_seconds,
            policy.retry_max_seconds,
        )

    def _interrupt(self, activity_id, *, now, reason, pets):
        activity = self.coordinator.get_activity(activity_id)
        normal_execution = bool(
            activity is not None
            and str(activity.metadata.get("execution_mode", ""))
            != RACE_EXECUTION_SANDBOX_PREVIEW
        )
        transition = self.coordinator.interrupt(
            activity_id,
            now=float(now),
            reason=str(reason or ""),
            force=True,
        )
        pets_by_name = self._pets_by_name(pets)
        self.runtime_adapter.clear_released_participants(
            pets_by_name,
            transition.released_participant_names,
            expected_activity_id=activity_id,
        )
        if transition.handled and normal_execution:
            self._schedule_retry(
                now,
                world_mode=str(
                    activity.metadata.get("world_mode", "golden_legend")
                ),
            )
        return RaceRuntimeResult(
            transition.handled,
            reason=str(reason or transition.reason),
            activity_id=activity_id,
            finished=transition.finished,
            interrupted=transition.handled,
        )

    def _eligibility_decision(self, pet, *, now, world_mode, preview):
        name = self._pet_name(pet)
        form_key = get_pet_form_key(pet)
        profile_ready = race_profile_supports_form(name, form_key)
        form_ready = pet_form_allows_capability(pet, CAPABILITY_RACE)
        snapshot = self.runtime_adapter.build_participant_snapshot(
            pet,
            role=RACE_CHALLENGER_ROLE,
            now=now,
        )
        return evaluate_race_eligibility(
            RaceEligibilitySnapshot(
                character_name=name,
                form_key=form_key,
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
                capability_ready=bool(profile_ready and form_ready),
            ),
            preview=preview,
        )

    def _emergency_decision(self, pets):
        distressed_child_names = []
        tsuyoshi_has_honey = False
        for pet in pets or ():
            name = self._pet_name(pet)
            if (
                name == "Tsurumaru Tsuyoshi"
                and str(getattr(pet, "held_item_kind", "") or "") == "honey"
            ):
                tsuyoshi_has_honey = True
            if bool(getattr(pet, "is_adult", False)):
                continue
            care_enabled = getattr(pet, "is_care_feature_enabled", None)
            if callable(care_enabled) and not bool(care_enabled()):
                continue
            is_distressed = getattr(pet, "is_distressed", None)
            if callable(is_distressed) and bool(is_distressed()):
                distressed_child_names.append(name)
        return evaluate_race_emergency_interrupt(
            RaceEmergencySnapshot(
                distressed_child_names=tuple(distressed_child_names),
                tsuyoshi_has_honey=tsuyoshi_has_honey,
            )
        )

    def _move_pet(self, pet, target_x, *, speed_scale, min_speed=None):
        if pet is None:
            return False
        pet.direction = 1 if float(target_x) >= self._pet_x(pet) else -1
        mover = getattr(pet, "move_toward_x", None)
        if not callable(mover):
            return abs(self._pet_x(pet) - float(target_x)) <= RACE_ARRIVAL_DISTANCE
        arrived = bool(
            mover(
                float(target_x),
                speed_scale=float(speed_scale),
                min_speed=min_speed,
            )
        )
        return arrived or abs(self._pet_x(pet) - float(target_x)) <= RACE_ARRIVAL_DISTANCE

    def _move_pet_precise(
        self,
        activity,
        pet,
        target_x,
        *,
        speed: float,
        remainder_key: str,
    ) -> bool:
        if pet is None:
            return False
        base_speed_getter = getattr(pet, "get_base_speed", None)
        base_speed = (
            float(base_speed_getter())
            if callable(base_speed_getter)
            else 0.0
        )
        exact_step = (
            max(base_speed, float(speed)) * RACE_RUNNING_SPEED_SCALE
            + float(activity.metadata.get(remainder_key, 0.0) or 0.0)
        )
        integer_step = max(1, int(math.floor(exact_step)))
        activity.metadata[remainder_key] = max(
            0.0,
            exact_step - float(integer_step),
        )
        return self._move_pet(
            pet,
            target_x,
            speed_scale=1.0,
            min_speed=float(integer_step),
        )

    def _clamp_target_for_pet(self, pet, target_x: float) -> float:
        if pet is None:
            return float(target_x)
        snapshot_getter = getattr(pet, "get_surface_snapshot", None)
        if not callable(snapshot_getter):
            return float(target_x)
        surface = snapshot_getter()
        clamp_x = getattr(surface, "clamp_x", None)
        return float(clamp_x(target_x)) if callable(clamp_x) else float(target_x)

    def _replan_lane(self, activity, challenger, opponent, *, now: float) -> None:
        left_bound, right_bound = self.bounds_provider((challenger, opponent))
        lane = build_race_lane_geometry(
            left_bound=left_bound,
            right_bound=right_bound,
            participant_widths=(
                self._pet_width(challenger),
                self._pet_width(opponent),
            ),
            participant_radii=(
                self._pet_radius(challenger),
                self._pet_radius(opponent),
            ),
            participant_positions=(
                self._pet_x(challenger),
                self._pet_x(opponent),
            ),
        )
        activity.metadata.update({
            "challenger_start_x": lane.challenger_start_x,
            "opponent_start_x": lane.opponent_start_x,
            "finish_x": lane.finish_x,
            "challenger_finish_x": (
                lane.challenger_start_x + (lane.direction * lane.distance)
            ),
            "opponent_finish_x": (
                lane.opponent_start_x + (lane.direction * lane.distance)
            ),
            "race_direction": lane.direction,
            "race_distance": lane.distance,
            "to_start_last_progress_at": float(now),
            "to_start_last_distance": 0.0,
        })

    def _performance_decision(self, challenger, opponent):
        return decide_race_performance(
            challenger_name=self._pet_name(challenger),
            challenger_form=get_pet_form_key(challenger),
            challenger_mood_score=float(
                getattr(challenger, "mood_score", 60.0)
            ),
            challenger_roll=self.random_value(),
            opponent_name=self._pet_name(opponent),
            opponent_form=get_pet_form_key(opponent),
            opponent_mood_score=float(
                getattr(opponent, "mood_score", 60.0)
            ),
            opponent_roll=self.random_value(),
        )

    def _pair_spacing_reason(self, first, second):
        return race_pair_spacing_reason(
            self._pet_center_distance(first, second),
            participant_radii=(
                self._pet_radius(first),
                self._pet_radius(second),
            ),
        )

    def _pair_is_close(self, first, second):
        return not self._pair_spacing_reason(first, second)

    def _apply_phase_facing(self, activity, pets_by_name):
        challenger = pets_by_name.get(
            str(activity.metadata.get("challenger_name", ""))
        )
        opponent = pets_by_name.get(
            str(activity.metadata.get("opponent_name", ""))
        )
        if activity.phase.name in {
            RACE_RESPONSE_PHASE,
            RACE_FINISH_PHASE,
        }:
            self._face_each_other(challenger, opponent)
            return
        if activity.phase.name not in {
            RACE_READY_PHASE,
            RACE_RUNNING_PHASE,
        }:
            return
        finish_x = float(activity.metadata.get("finish_x", 0.0))
        for pet in (challenger, opponent):
            if pet is not None:
                pet.direction = 1 if finish_x >= self._pet_x(pet) else -1

    def _prime_post_race_interaction(self, activity, pets_by_name, *, now):
        challenger = pets_by_name.get(
            str(activity.metadata.get("challenger_name", ""))
        )
        opponent = pets_by_name.get(
            str(activity.metadata.get("opponent_name", ""))
        )
        for pet, partner in ((challenger, opponent), (opponent, challenger)):
            if pet is None or partner is None:
                continue
            current_social_cooldown = float(
                getattr(pet, "social_cooldown_end", 0.0) or 0.0
            )
            pet.social_cooldown_end = min(current_social_cooldown, float(now))
            current_reconsider_after = float(
                getattr(pet, "intent_reconsider_after", 0.0) or 0.0
            )
            pet.intent_reconsider_after = min(
                current_reconsider_after,
                float(now),
            )
            if str(
                getattr(pet, "observe_blocked_target_name", "") or ""
            ) == self._pet_name(partner):
                pet.observe_blocked_target_name = ""
                pet.observe_blocked_until = 0.0
            starter = getattr(pet, "start_post_observe_interaction", None)
            if callable(starter) and self._pet_is_visible(partner):
                starter(
                    partner,
                    float(now),
                    "relation_watch",
                    RACE_POST_INTERACTION_SECONDS,
                )

    def _active_race(self):
        return next(
            (
                activity
                for activity in self.coordinator.get_active_activities()
                if activity.spec.kind == RACE_ACTIVITY_KIND
            ),
            None,
        )

    def _sample(self, minimum, maximum):
        return max(
            float(minimum),
            min(float(maximum), float(self.uniform(minimum, maximum))),
        )

    def _roll_index(self, length):
        return min(max(0, int(float(self.random_value()) * length)), length - 1)

    @staticmethod
    def _default_bounds(pets):
        rect = get_total_virtual_geometry()
        if rect.isNull():
            positions = [RaceExecutor._pet_x(pet) for pet in pets]
            left = min(positions, default=0.0)
            return left, left + 900.0
        return float(rect.left()), float(rect.right())

    @staticmethod
    def _pet_name(pet):
        return str(getattr(pet, "name", "") or "").strip()

    @classmethod
    def _pets_by_name(cls, pets):
        return {
            cls._pet_name(pet): pet
            for pet in pets or ()
            if cls._pet_name(pet)
        }

    @staticmethod
    def _pet_is_visible(pet):
        if pet is None or not bool(getattr(pet, "user_visible", True)):
            return False
        is_visible = getattr(pet, "isVisible", None)
        return bool(is_visible()) if callable(is_visible) else True

    @staticmethod
    def _pet_x(pet):
        getter = getattr(pet, "x", None)
        return float(getter() if callable(getter) else getattr(pet, "x", 0.0))

    @staticmethod
    def _pet_width(pet):
        getter = getattr(pet, "width", None)
        return max(
            1.0,
            float(getter() if callable(getter) else getattr(pet, "width", 100.0)),
        )

    @staticmethod
    def _pet_radius(pet):
        return max(0.0, float(getattr(pet, "radius", 50.0) or 0.0))

    @classmethod
    def _pet_center_distance(cls, first, second):
        if first is None or second is None:
            return float("inf")
        first_center = cls._pet_x(first) + (cls._pet_width(first) / 2.0)
        second_center = cls._pet_x(second) + (cls._pet_width(second) / 2.0)
        return abs(first_center - second_center)

    @classmethod
    def _face_each_other(cls, first, second):
        if first is None or second is None:
            return
        first.direction = 1 if cls._pet_x(second) >= cls._pet_x(first) else -1
        second.direction = -first.direction
