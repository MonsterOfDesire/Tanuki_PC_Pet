from __future__ import annotations

from dataclasses import dataclass


AI_STAGE_CARE = "care"
AI_STAGE_SOCIAL = "social"
AI_STAGE_POST_OBSERVE = "post_observe"
AI_STAGE_OBSERVE = "observe"
AI_STAGE_AMBIENT_MOOD = "ambient_mood"


@dataclass(frozen=True)
class PetAiStagePlan:
    stages: tuple[str, ...]
    high_level_allowed: bool


def build_pet_ai_stage_plan(
    *,
    should_attempt_followup,
    care_lock_maintained,
    active_post_observe,
    active_observe,
    refresh_high_level,
):
    if not should_attempt_followup or care_lock_maintained:
        return PetAiStagePlan((), False)
    high_level_allowed = bool(
        active_post_observe
        or active_observe
        or refresh_high_level
    )
    stages = [AI_STAGE_CARE, AI_STAGE_SOCIAL]
    if high_level_allowed:
        stages.extend((
            AI_STAGE_POST_OBSERVE,
            AI_STAGE_OBSERVE,
            AI_STAGE_AMBIENT_MOOD,
        ))
    return PetAiStagePlan(tuple(stages), high_level_allowed)
