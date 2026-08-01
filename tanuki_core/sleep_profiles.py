from __future__ import annotations

from dataclasses import dataclass

from .activity_profiles import ActivityAnimationBinding
from .manifest_animation_resolver import ManifestAnimationResolver
from .sleep_rules import (
    SLEEP_PROFILE_KEY,
    SLEEP_ROLE,
    SLEEP_SETTLING_PHASE,
    SLEEP_WAKING_PHASE,
    SLEEPING_PHASE,
    build_sleep_activity_spec,
)


@dataclass(frozen=True)
class SleepCapabilityDecision:
    ready: bool
    reason: str = ""
    phase_name: str = ""


@dataclass(frozen=True)
class SleepProfile:
    profile_key: str
    participant_role: str
    settling_animation: ActivityAnimationBinding
    sleeping_animation: ActivityAnimationBinding
    waking_animation: ActivityAnimationBinding
    observing_animation: ActivityAnimationBinding
    join_approach_animation: ActivityAnimationBinding
    join_settling_animation: ActivityAnimationBinding

    def animation_for_phase(
        self,
        phase_name: str,
    ) -> ActivityAnimationBinding | None:
        if phase_name == SLEEP_SETTLING_PHASE:
            return self.settling_animation
        if phase_name == SLEEPING_PHASE:
            return self.sleeping_animation
        if phase_name == SLEEP_WAKING_PHASE:
            return self.waking_animation
        return None

    def build_activity_spec(self, sleeping_seconds: float):
        return build_sleep_activity_spec(sleeping_seconds)


SLEEP_PROFILE = SleepProfile(
    profile_key=SLEEP_PROFILE_KEY,
    participant_role=SLEEP_ROLE,
    settling_animation=ActivityAnimationBinding(
        contexts=("activity_sleep_settling",),
    ),
    sleeping_animation=ActivityAnimationBinding(
        contexts=("activity_sleeping",),
    ),
    waking_animation=ActivityAnimationBinding(
        contexts=("activity_sleep_waking",),
    ),
    observing_animation=ActivityAnimationBinding(
        contexts=("activity_sleep_observing",),
    ),
    join_approach_animation=ActivityAnimationBinding(
        contexts=("activity_sleep_join_approach",),
    ),
    join_settling_animation=ActivityAnimationBinding(
        contexts=(
            "activity_sleep_join_settling",
            "activity_sleep_settling",
        ),
    ),
)


def evaluate_sleep_capability(
    asset_manager,
    *,
    mood_score: float,
    resolver: ManifestAnimationResolver | None = None,
    profile: SleepProfile = SLEEP_PROFILE,
) -> SleepCapabilityDecision:
    resolver = resolver or ManifestAnimationResolver()
    spec = profile.build_activity_spec(1.0)
    for phase in spec.phases:
        binding = profile.animation_for_phase(phase.name)
        if binding is None:
            return SleepCapabilityDecision(
                False,
                "missing_phase_binding",
                phase.name,
            )
        resolution = resolver.resolve(
            asset_manager,
            binding.build_request(mood_score),
        )
        if not resolution.found:
            return SleepCapabilityDecision(
                False,
                resolution.reason or "animation_unavailable",
                phase.name,
            )
    return SleepCapabilityDecision(True)


def evaluate_sleep_join_capability(
    asset_manager,
    *,
    mood_score: float,
    resolver: ManifestAnimationResolver | None = None,
    profile: SleepProfile = SLEEP_PROFILE,
) -> SleepCapabilityDecision:
    resolver = resolver or ManifestAnimationResolver()
    bindings = (
        ("observing", profile.observing_animation),
        ("approaching", profile.join_approach_animation),
        ("settling", profile.join_settling_animation),
        (SLEEPING_PHASE, profile.sleeping_animation),
        (SLEEP_WAKING_PHASE, profile.waking_animation),
    )
    for phase_name, binding in bindings:
        resolution = resolver.resolve(
            asset_manager,
            binding.build_request(mood_score),
        )
        if not resolution.found:
            return SleepCapabilityDecision(
                False,
                resolution.reason or "animation_unavailable",
                phase_name,
            )
    return SleepCapabilityDecision(True)
