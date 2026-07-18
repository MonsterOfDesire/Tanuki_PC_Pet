from dataclasses import dataclass

from .pet_logic import (
    AI_FOLLOWUP_CARE,
    AI_FOLLOWUP_CARE_LOCK,
    AI_FOLLOWUP_RANDOM,
    AI_FOLLOWUP_SOCIAL,
    AI_PHASE_ANGRY_LOCKED,
    AI_PHASE_RECOVERY_ACTIVE,
    AI_PHASE_RECOVERY_FINISHED,
    TICK_PHASE_DRAGGING,
    TICK_PHASE_RUN_AI,
    TICK_PHASE_WINDOW_FLIGHT,
    TICK_PHASE_WINDOW_PERCH,
    decide_followup_ai_phase,
    decide_initial_ai_phase,
    decide_tick_phase,
)
from .pet_intent_rules import resolve_intent_reselect_gate


@dataclass(frozen=True)
class TickWindowPlan:
    try_window_perch: bool
    try_window_flight: bool


@dataclass(frozen=True)
class TickExecutionPlan:
    phase: str
    should_apply_gravity: bool
    should_check_boundary_stuck: bool
    should_run_ai: bool
    should_refresh_and_return: bool


@dataclass(frozen=True)
class InitialAiPlan:
    phase: str
    should_move_recovery_walk: bool
    should_finish_recovery: bool
    should_attempt_followup: bool
    should_refresh_and_return: bool


@dataclass(frozen=True)
class FollowupAiPlan:
    phase: str
    should_run_random: bool
    should_refresh_and_return: bool


@dataclass(frozen=True)
class IntentReselectPlan:
    allow_reselect: bool
    next_reconsider_after: float | None
    reason: str


class PetTickCoordinator:
    def build_tick_window_plan(self, dragging):
        if dragging:
            return TickWindowPlan(
                try_window_perch=False,
                try_window_flight=False,
            )
        return TickWindowPlan(
            try_window_perch=True,
            try_window_flight=True,
        )

    def resolve_tick_execution_plan(
        self,
        dragging,
        window_perch_handled,
        window_flight_handled,
        vertical_velocity,
    ):
        phase = decide_tick_phase(
            dragging=dragging,
            window_perch_handled=window_perch_handled,
            window_flight_handled=window_flight_handled,
            vertical_velocity=vertical_velocity,
        )
        should_refresh_and_return = phase in {
            TICK_PHASE_DRAGGING,
            TICK_PHASE_WINDOW_PERCH,
            TICK_PHASE_WINDOW_FLIGHT,
        }
        return TickExecutionPlan(
            phase=phase,
            should_apply_gravity=not should_refresh_and_return,
            should_check_boundary_stuck=not should_refresh_and_return,
            should_run_ai=phase == TICK_PHASE_RUN_AI,
            should_refresh_and_return=should_refresh_and_return,
        )

    def resolve_initial_ai_plan(
        self,
        is_angry_locked,
        is_recovering,
        recovery_expired,
        recovery_motion_mode,
        current_purpose,
    ):
        phase = decide_initial_ai_phase(
            is_angry_locked=is_angry_locked,
            is_recovering=is_recovering,
            recovery_expired=recovery_expired,
        )
        if phase == AI_PHASE_ANGRY_LOCKED:
            return InitialAiPlan(
                phase=phase,
                should_move_recovery_walk=False,
                should_finish_recovery=False,
                should_attempt_followup=False,
                should_refresh_and_return=True,
            )
        if phase == AI_PHASE_RECOVERY_ACTIVE:
            return InitialAiPlan(
                phase=phase,
                should_move_recovery_walk=(recovery_motion_mode == "walk" and current_purpose == "move"),
                should_finish_recovery=False,
                should_attempt_followup=False,
                should_refresh_and_return=True,
            )
        if phase == AI_PHASE_RECOVERY_FINISHED:
            return InitialAiPlan(
                phase=phase,
                should_move_recovery_walk=False,
                should_finish_recovery=True,
                should_attempt_followup=True,
                should_refresh_and_return=False,
            )
        return InitialAiPlan(
            phase=phase,
            should_move_recovery_walk=False,
            should_finish_recovery=False,
            should_attempt_followup=True,
            should_refresh_and_return=False,
        )

    def resolve_followup_ai_plan(self, care_lock_maintained, care_behavior_handled, social_behavior_handled):
        phase = decide_followup_ai_phase(
            care_lock_maintained=care_lock_maintained,
            care_behavior_handled=care_behavior_handled,
            social_behavior_handled=social_behavior_handled,
        )
        return FollowupAiPlan(
            phase=phase,
            should_run_random=(phase == AI_FOLLOWUP_RANDOM),
            should_refresh_and_return=phase in {
                AI_FOLLOWUP_CARE_LOCK,
                AI_FOLLOWUP_CARE,
                AI_FOLLOWUP_SOCIAL,
            },
        )

    def resolve_intent_reselect_plan(
        self,
        *,
        now,
        intent_kind,
        intent_reconsider_after,
        dragging,
        is_angry_locked,
        is_recovering,
        care_lock_maintained,
        care_mode,
        social_mode,
        flight_mode,
        perched_window_hwnd,
    ):
        rule_plan = resolve_intent_reselect_gate(
            now=now,
            intent_kind=intent_kind,
            intent_reconsider_after=intent_reconsider_after,
            dragging=dragging,
            is_angry_locked=is_angry_locked,
            is_recovering=is_recovering,
            care_lock_active=care_lock_maintained,
            care_mode=care_mode,
            social_mode=social_mode,
            flight_mode=flight_mode,
            perched_window_hwnd=perched_window_hwnd,
        )
        return IntentReselectPlan(
            allow_reselect=rule_plan.allow_reselect,
            next_reconsider_after=rule_plan.next_reconsider_after,
            reason=rule_plan.reason,
        )
