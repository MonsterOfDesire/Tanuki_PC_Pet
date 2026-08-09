from __future__ import annotations

from dataclasses import dataclass

from .activity_profiles import ActivityAnimationBinding
from .chorus_rules import (
    CHORUS_APPROACH_PHASE,
    CHORUS_FINISH_PHASE,
    CHORUS_OBSERVE_PHASE,
    CHORUS_PERFORM_PHASE,
)
from .manifest_animation_resolver import ManifestAnimationResolver


@dataclass(frozen=True)
class ChorusAnimationCapabilities:
    approach: bool
    perform: bool
    observe: bool
    finish: bool


@dataclass(frozen=True)
class ChorusProfile:
    approach_animation: ActivityAnimationBinding
    perform_animation: ActivityAnimationBinding
    observe_animation: ActivityAnimationBinding
    finish_animation: ActivityAnimationBinding

    def animation_for_phase(self, phase_name: str):
        return {
            CHORUS_APPROACH_PHASE: self.approach_animation,
            CHORUS_PERFORM_PHASE: self.perform_animation,
            CHORUS_OBSERVE_PHASE: self.observe_animation,
            CHORUS_FINISH_PHASE: self.finish_animation,
        }.get(str(phase_name or ""))


CHORUS_PROFILE = ChorusProfile(
    approach_animation=ActivityAnimationBinding(
        contexts=("activity_chorus_approach",),
    ),
    perform_animation=ActivityAnimationBinding(
        contexts=("activity_chorus_perform",),
    ),
    observe_animation=ActivityAnimationBinding(
        contexts=("activity_chorus_observe",),
    ),
    finish_animation=ActivityAnimationBinding(
        contexts=("activity_chorus_finish",),
    ),
)


def evaluate_chorus_capabilities(
    asset_manager,
    *,
    mood_score: float,
    resolver: ManifestAnimationResolver | None = None,
    profile: ChorusProfile = CHORUS_PROFILE,
) -> ChorusAnimationCapabilities:
    resolver = resolver or ManifestAnimationResolver()

    def available(binding):
        return resolver.resolve(
            asset_manager,
            binding.build_request(float(mood_score)),
        ).found

    return ChorusAnimationCapabilities(
        approach=available(profile.approach_animation),
        perform=available(profile.perform_animation),
        observe=available(profile.observe_animation),
        finish=available(profile.finish_animation),
    )
