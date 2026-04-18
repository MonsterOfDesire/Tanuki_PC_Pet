from dataclasses import dataclass
from typing import Any, Optional, Sequence

from .pet_social_rules import (
    CARE_PLAN_COMPANION,
    CARE_PLAN_INTERACTION,
    CareTargetCandidate,
    SOCIAL_ENTRY_FOLLOWING,
    SOCIAL_ENTRY_MIMICKING,
    choose_care_target,
    decide_care_plan,
    decide_social_entry as rule_decide_social_entry,
)


CARE_DECISION_NONE = "none"
CARE_DECISION_CONTINUE = "continue"
CARE_DECISION_CANCEL = "cancel"
CARE_DECISION_FINISH_SUCCESS = "finish_success"
CARE_DECISION_FINISH_FAILURE = "finish_failure"
CARE_DECISION_INTERACTION_TICK = "interaction_tick"
CARE_DECISION_MOVING_INTERACTION_TICK = "moving_interaction_tick"
CARE_DECISION_SIT_TICK = "sit_tick"
CARE_DECISION_APPROACH_TICK = "approach_tick"
CARE_DECISION_START_APPROACH = "start_approach"

CARE_TRANSITION_NONE = "none"
CARE_TRANSITION_INTERACTION = "interaction"
CARE_TRANSITION_COMPANION = "companion"

SOCIAL_DECISION_NONE = "none"
SOCIAL_DECISION_CONTINUE = "continue"
SOCIAL_DECISION_STOP = "stop"
SOCIAL_DECISION_ACTIVE_FOLLOWING = "active_following"
SOCIAL_DECISION_ACTIVE_MIMICKING = "active_mimicking"
SOCIAL_DECISION_START_FOLLOWING = "start_following"
SOCIAL_DECISION_START_MIMICKING = "start_mimicking"


@dataclass(frozen=True)
class CareDecision:
    action: str
    handled: bool = False
    target: Any = None
    next_care_plan: Optional[str] = None
    use_interaction: bool = False
    target_x: Optional[int] = None


@dataclass(frozen=True)
class ActiveCareContext:
    has_child: bool
    child_in_all_pets: bool
    child_partner_ok: bool
    child_visible: bool
    mode: str
    now: float
    care_end_time: float
    child_mood_score: float
    child_is_distressed: bool
    care_plan: str
    interaction_available: bool
    adult_name: str
    adult_x: int
    child_x: int
    distance_to_child: float
    moving_interaction_hits_edge: bool
    roll: float


@dataclass(frozen=True)
class IdleCareContext:
    now: float
    care_cooldown_end: float
    adult: Any
    adult_name: str
    target_candidates: Sequence[CareTargetCandidate]


@dataclass(frozen=True)
class SocialDecision:
    action: str
    handled: bool = False


@dataclass(frozen=True)
class ActiveSocialContext:
    social_mode: str
    has_rudolf: bool
    social_target_matches: bool
    distance_to_rudolf: float
    timer_frames_remaining: int
    social_distance: float
    rudolf_purpose: str
    can_mimic: bool


@dataclass(frozen=True)
class SocialEntryContext:
    has_rudolf: bool
    now: float
    social_cooldown_end: float
    distance_to_rudolf: float
    social_distance: float
    rudolf_purpose: str
    is_behind: bool
    can_strictly_mimic: bool
    can_mimic: bool


class SocialCareCoordinator:
    def decide_care_gate(self, *, is_adult, is_visible, care_enabled, care_mode):
        if not is_adult or not is_visible or not care_enabled:
            if care_mode != "none":
                return CareDecision(action=CARE_DECISION_CANCEL)
            return CareDecision(action=CARE_DECISION_NONE)
        return CareDecision(action=CARE_DECISION_CONTINUE)

    def decide_active_care(self, context: ActiveCareContext):
        if (
            not context.has_child or
            not context.child_in_all_pets or
            not context.child_partner_ok or
            (not context.child_visible and context.mode not in {"interaction", "moving_interaction"})
        ):
            return CareDecision(action=CARE_DECISION_CANCEL)

        if context.mode == "interaction":
            if context.now >= context.care_end_time:
                return CareDecision(action=CARE_DECISION_FINISH_SUCCESS, handled=True)
            return CareDecision(action=CARE_DECISION_INTERACTION_TICK, handled=True)

        if context.mode == "moving_interaction":
            if context.now >= context.care_end_time or context.moving_interaction_hits_edge:
                return CareDecision(action=CARE_DECISION_FINISH_SUCCESS, handled=True)
            return CareDecision(action=CARE_DECISION_MOVING_INTERACTION_TICK, handled=True)

        if context.mode == "sit":
            if context.now >= context.care_end_time or context.child_mood_score >= 70:
                return CareDecision(action=CARE_DECISION_FINISH_SUCCESS, handled=True)
            return CareDecision(action=CARE_DECISION_SIT_TICK, handled=True)

        if not context.child_is_distressed and context.child_mood_score >= 55:
            return CareDecision(action=CARE_DECISION_FINISH_FAILURE)

        next_care_plan = context.care_plan
        if next_care_plan == "auto":
            next_care_plan = decide_care_plan(
                context.adult_name,
                context.interaction_available,
                context.roll,
            )
        elif next_care_plan == CARE_PLAN_INTERACTION and not context.interaction_available:
            next_care_plan = CARE_PLAN_COMPANION

        use_interaction = next_care_plan == CARE_PLAN_INTERACTION and context.interaction_available
        offset = 120 if context.adult_x <= context.child_x else -120
        target_x = context.child_x if use_interaction else context.child_x - offset
        return CareDecision(
            action=CARE_DECISION_APPROACH_TICK,
            handled=True,
            next_care_plan=next_care_plan,
            use_interaction=use_interaction,
            target_x=target_x,
        )

    def decide_idle_care(self, context: IdleCareContext):
        if context.now < context.care_cooldown_end:
            return CareDecision(action=CARE_DECISION_NONE)

        target = choose_care_target(context.adult, context.adult_name, context.target_candidates)
        if target is None:
            return CareDecision(action=CARE_DECISION_NONE)
        return CareDecision(action=CARE_DECISION_START_APPROACH, handled=True, target=target)

    def decide_approach_transition(self, *, arrived, distance_to_child, use_interaction):
        if not arrived and distance_to_child >= 140:
            return CARE_TRANSITION_NONE
        if use_interaction:
            return CARE_TRANSITION_INTERACTION
        return CARE_TRANSITION_COMPANION

    def decide_social_gate(self, *, is_social_child, dragging):
        if not is_social_child or dragging:
            return SocialDecision(action=SOCIAL_DECISION_NONE)
        return SocialDecision(action=SOCIAL_DECISION_CONTINUE)

    def decide_active_social(self, context: ActiveSocialContext):
        if not context.has_rudolf or not context.social_target_matches:
            return SocialDecision(action=SOCIAL_DECISION_STOP)

        timed_out = context.timer_frames_remaining <= 0
        if timed_out or context.distance_to_rudolf > (context.social_distance + 150):
            return SocialDecision(action=SOCIAL_DECISION_STOP)

        if context.social_mode == "following":
            if context.rudolf_purpose != "move":
                return SocialDecision(action=SOCIAL_DECISION_STOP)
            return SocialDecision(action=SOCIAL_DECISION_ACTIVE_FOLLOWING, handled=True)

        if context.social_mode == "mimicking":
            if not context.can_mimic:
                return SocialDecision(action=SOCIAL_DECISION_STOP)
            return SocialDecision(action=SOCIAL_DECISION_ACTIVE_MIMICKING, handled=True)

        return SocialDecision(action=SOCIAL_DECISION_NONE)

    def decide_social_entry(self, context: SocialEntryContext):
        if not context.has_rudolf or context.now < context.social_cooldown_end:
            return SocialDecision(action=SOCIAL_DECISION_NONE)

        entry = rule_decide_social_entry(
            distance=context.distance_to_rudolf,
            social_distance=context.social_distance,
            rudolf_purpose=context.rudolf_purpose,
            is_behind=context.is_behind,
            can_strictly_mimic=context.can_strictly_mimic,
            can_mimic=context.can_mimic,
        )
        if entry == SOCIAL_ENTRY_FOLLOWING:
            return SocialDecision(action=SOCIAL_DECISION_START_FOLLOWING, handled=True)
        if entry == SOCIAL_ENTRY_MIMICKING:
            return SocialDecision(action=SOCIAL_DECISION_START_MIMICKING, handled=True)
        return SocialDecision(action=SOCIAL_DECISION_NONE)


SOCIAL_CARE_COORDINATOR = SocialCareCoordinator()
