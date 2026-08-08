from __future__ import annotations

from dataclasses import dataclass

from .activity_profiles import ActivityAnimationBinding
from .manifest_animation_resolver import ManifestAnimationResolver
from .race_rules import (
    RACE_CHALLENGE_PHASE,
    RACE_FINISH_PHASE,
    RACE_PROFILE_KEY,
    RACE_READY_PHASE,
    RACE_RECOVERY_PHASE,
    RACE_RESPONSE_PHASE,
    RACE_RUNNING_PHASE,
    RACE_TO_START_PHASE,
    build_race_activity_spec,
    resolve_race_finish_band,
)


RACE_SUPPORTED_NAMES = frozenset(
    {
        "Tokai Teio",
        "Sirius Symboli",
        "Symboli Rudolf",
    }
)


@dataclass(frozen=True)
class RaceAnimationRequirement:
    phase_name: str
    binding: ActivityAnimationBinding
    band_override: str = ""


@dataclass(frozen=True)
class RaceCapabilityDecision:
    ready: bool
    reason: str = ""
    phase_name: str = ""


@dataclass(frozen=True)
class RaceProfile:
    profile_key: str
    activity_spec: object
    challenge_animation: ActivityAnimationBinding
    consider_animation: ActivityAnimationBinding
    accept_animation: ActivityAnimationBinding
    decline_animation: ActivityAnimationBinding
    to_start_animation: ActivityAnimationBinding
    ready_animation: ActivityAnimationBinding
    running_animation: ActivityAnimationBinding
    finish_win_animation: ActivityAnimationBinding
    finish_lose_animation: ActivityAnimationBinding
    recovery_animation: ActivityAnimationBinding
    sirius_teio_running_animation: ActivityAnimationBinding

    def response_animation(self, accepted: bool) -> ActivityAnimationBinding:
        return self.accept_animation if accepted else self.decline_animation

    def running_animation_for(
        self,
        character_name: str,
        opponent_name: str,
        *,
        opponent_form: str = "base",
    ) -> ActivityAnimationBinding:
        if (
            str(character_name or "") == "Sirius Symboli"
            and str(opponent_name or "") == "Tokai Teio"
            and str(opponent_form or "base") == "base"
        ):
            return self.sirius_teio_running_animation
        return self.running_animation


RACE_PROFILE = RaceProfile(
    profile_key=RACE_PROFILE_KEY,
    activity_spec=build_race_activity_spec(),
    challenge_animation=ActivityAnimationBinding(
        contexts=("activity_race_challenge",),
    ),
    consider_animation=ActivityAnimationBinding(
        contexts=("activity_race_consider",),
    ),
    accept_animation=ActivityAnimationBinding(
        contexts=("activity_race_accept",),
    ),
    decline_animation=ActivityAnimationBinding(
        contexts=("activity_race_decline",),
    ),
    to_start_animation=ActivityAnimationBinding(
        contexts=("activity_race_to_start",),
    ),
    ready_animation=ActivityAnimationBinding(
        contexts=("activity_race_ready",),
    ),
    running_animation=ActivityAnimationBinding(
        contexts=("activity_race_running",),
    ),
    finish_win_animation=ActivityAnimationBinding(
        contexts=("activity_race_finish_win",),
    ),
    finish_lose_animation=ActivityAnimationBinding(
        contexts=("activity_race_finish_lose",),
    ),
    recovery_animation=ActivityAnimationBinding(
        contexts=("activity_race_recovery",),
    ),
    sirius_teio_running_animation=ActivityAnimationBinding(
        contexts=("activity_race_running_teio",),
    ),
)


def race_profile_supports_form(character_name: str, form_key: str) -> bool:
    name = str(character_name or "")
    form = str(form_key or "base")
    if name not in RACE_SUPPORTED_NAMES:
        return False
    if name == "Tokai Teio" and form == "transformed":
        return False
    if name == "Sirius Symboli" and form != "base":
        return False
    return form in {"base", "transformed"}


def evaluate_race_capability(
    asset_manager,
    *,
    mood_score: float,
    requirements: tuple[RaceAnimationRequirement, ...],
    resolver: ManifestAnimationResolver | None = None,
) -> RaceCapabilityDecision:
    resolver = resolver or ManifestAnimationResolver()
    for requirement in requirements:
        resolution = resolver.resolve(
            asset_manager,
            requirement.binding.build_request(
                mood_score,
                band_override=requirement.band_override,
            ),
        )
        if not resolution.found:
            return RaceCapabilityDecision(
                False,
                resolution.reason or "animation_unavailable",
                requirement.phase_name,
            )
    return RaceCapabilityDecision(True)


def build_race_requirements(
    *,
    character_name: str,
    opponent_name: str,
    opponent_form: str,
    role: str,
    accepted: bool,
    winner: bool | None = False,
    transformed: bool = False,
    profile: RaceProfile = RACE_PROFILE,
) -> tuple[RaceAnimationRequirement, ...]:
    if role == "challenger":
        requirements = [
            RaceAnimationRequirement(
                RACE_CHALLENGE_PHASE,
                profile.challenge_animation,
            )
        ]
    else:
        requirements = [
            RaceAnimationRequirement(
                RACE_CHALLENGE_PHASE,
                profile.consider_animation,
            ),
            RaceAnimationRequirement(
                RACE_RESPONSE_PHASE,
                profile.response_animation(accepted),
            )
        ]
    if not accepted:
        return tuple(requirements)
    requirements.extend(
        (
            RaceAnimationRequirement(
                RACE_TO_START_PHASE,
                profile.to_start_animation,
            ),
            RaceAnimationRequirement(
                RACE_READY_PHASE,
                profile.ready_animation,
            ),
            RaceAnimationRequirement(
                RACE_RUNNING_PHASE,
                profile.running_animation_for(
                    character_name,
                    opponent_name,
                    opponent_form=opponent_form,
                ),
            ),
        )
    )
    finish_outcomes = (True, False) if winner is None else (bool(winner),)
    for finish_winner in finish_outcomes:
        requirements.append(RaceAnimationRequirement(
            RACE_FINISH_PHASE,
            (
                profile.finish_win_animation
                if finish_winner
                else profile.finish_lose_animation
            ),
            band_override=resolve_race_finish_band(
                character_name=character_name,
                opponent_name=opponent_name,
                winner=finish_winner,
                transformed=transformed,
            ),
        ))
    requirements.append(RaceAnimationRequirement(
        RACE_RECOVERY_PHASE,
        profile.recovery_animation,
    ))
    return tuple(requirements)
