from __future__ import annotations

from dataclasses import dataclass

from .activity_profiles import ActivityAnimationBinding
from .activity_state import (
    ActivityPhaseSpec,
    ActivitySpec,
    COLLISION_POLICY_IGNORE,
    INTERRUPT_POLICY_ALLOW,
    INTERRUPT_POLICY_FORCE_ONLY,
)
from .asset_selection_rules import get_mood_band
from .manifest_animation_resolver import (
    BAND_POLICY_IGNORE,
    ManifestAnimationResolver,
)


RUDOLF_NAME = "Symboli Rudolf"
RUDOLF_WORK_ACTIVITY_KIND = "rudolf_work"
RUDOLF_WORK_PROFILE_KEY = "rudolf_work_v1"
RUDOLF_WORK_ROLE = "worker"

RUDOLF_WORK_WORKING_PHASE = "working"
RUDOLF_WORK_REST_PHASE = "post_work_rest"
RUDOLF_WORK_WORKING_SECONDS = 8.0
RUDOLF_WORK_REST_SECONDS = 3.0

RUDOLF_WORK_INCOME = 80
RUDOLF_WORK_PRESSURE_RELIEF = -6.0
RUDOLF_WORK_MOOD_DELTA = -6.0
WORK_LIVING_FUND_THRESHOLD = 820
WORK_PRESSURE_THRESHOLD = 28.0
RUDOLF_WORK_SETTLEMENT_KEY = "rudolf_work_v1"
RUDOLF_WORK_EXECUTION_NORMAL = "normal"
RUDOLF_WORK_EXECUTION_SANDBOX_PREVIEW = "sandbox_preview"

RUDOLF_WORK_BLOCKED_OPERATIONS = frozenset(
    {
        "random",
        "offer",
        "social_start",
        "observe_start",
        "care_give",
        "care_receive",
        "windowing",
        "drag",
    }
)


@dataclass(frozen=True)
class RudolfWorkProfile:
    profile_key: str
    character_name: str
    participant_role: str
    activity_spec: ActivitySpec
    working_animation: ActivityAnimationBinding
    rest_animation: ActivityAnimationBinding
    transport_animation: ActivityAnimationBinding
    enabled_work_modes: tuple[str, ...] = ("stationary",)

    def animation_for_phase(
        self,
        phase_name: str,
    ) -> ActivityAnimationBinding | None:
        if phase_name == RUDOLF_WORK_WORKING_PHASE:
            return self.working_animation
        if phase_name == RUDOLF_WORK_REST_PHASE:
            return self.rest_animation
        return None

    def animation_for_work_mode(
        self,
        mode: str,
    ) -> ActivityAnimationBinding | None:
        if mode == "stationary":
            return self.working_animation
        if mode == "transport":
            return self.transport_animation
        return None


def build_rudolf_work_activity_spec() -> ActivitySpec:
    return ActivitySpec(
        kind=RUDOLF_WORK_ACTIVITY_KIND,
        phases=(
            ActivityPhaseSpec(
                RUDOLF_WORK_WORKING_PHASE,
                RUDOLF_WORK_WORKING_SECONDS,
                interrupt_policy=INTERRUPT_POLICY_FORCE_ONLY,
            ),
            ActivityPhaseSpec(
                RUDOLF_WORK_REST_PHASE,
                RUDOLF_WORK_REST_SECONDS,
                interrupt_policy=INTERRUPT_POLICY_ALLOW,
            ),
        ),
        blocked_operations=RUDOLF_WORK_BLOCKED_OPERATIONS,
        collision_policy=COLLISION_POLICY_IGNORE,
        interrupt_policy=INTERRUPT_POLICY_ALLOW,
    )


RUDOLF_WORK_PROFILE = RudolfWorkProfile(
    profile_key=RUDOLF_WORK_PROFILE_KEY,
    character_name=RUDOLF_NAME,
    participant_role=RUDOLF_WORK_ROLE,
    activity_spec=build_rudolf_work_activity_spec(),
    working_animation=ActivityAnimationBinding(
        contexts=("activity_work_stationary",),
    ),
    rest_animation=ActivityAnimationBinding(
        contexts=("activity_work_rest",),
        band_policy=BAND_POLICY_IGNORE,
    ),
    transport_animation=ActivityAnimationBinding(
        contexts=("activity_work_transport",),
    ),
    enabled_work_modes=("stationary",),
)


@dataclass(frozen=True)
class RudolfWorkEligibilitySnapshot:
    character_name: str
    world_mode: str
    mood_score: float
    living_fund: int
    household_pressure: float
    now: float
    next_eligible_at: float = 0.0


@dataclass(frozen=True)
class RudolfWorkEligibilityDecision:
    allowed: bool
    reason: str = ""
    mood_band: str = ""


@dataclass(frozen=True)
class RudolfWorkCapabilityDecision:
    ready: bool
    reason: str = ""
    phase_name: str = ""


def should_household_request_rudolf_work(
    *,
    living_fund: int,
    household_pressure: float,
) -> bool:
    return (
        int(living_fund) <= WORK_LIVING_FUND_THRESHOLD
        or float(household_pressure) >= WORK_PRESSURE_THRESHOLD
    )


def evaluate_rudolf_work_eligibility(
    snapshot: RudolfWorkEligibilitySnapshot,
    *,
    profile: RudolfWorkProfile = RUDOLF_WORK_PROFILE,
) -> RudolfWorkEligibilityDecision:
    mood_band = get_mood_band(float(snapshot.mood_score))
    if str(snapshot.character_name or "") != profile.character_name:
        return RudolfWorkEligibilityDecision(
            False,
            "unsupported_character",
            mood_band,
        )
    if str(snapshot.world_mode or "") != "golden_legend":
        return RudolfWorkEligibilityDecision(
            False,
            "world_mode_disabled",
            mood_band,
        )
    if mood_band == "severe":
        return RudolfWorkEligibilityDecision(
            False,
            "severe_mood",
            mood_band,
        )
    if float(snapshot.now) < float(snapshot.next_eligible_at):
        return RudolfWorkEligibilityDecision(
            False,
            "cooldown_active",
            mood_band,
        )
    if not should_household_request_rudolf_work(
        living_fund=snapshot.living_fund,
        household_pressure=snapshot.household_pressure,
    ):
        return RudolfWorkEligibilityDecision(
            False,
            "household_stable",
            mood_band,
        )
    return RudolfWorkEligibilityDecision(True, mood_band=mood_band)


def evaluate_rudolf_work_preview_eligibility(
    snapshot: RudolfWorkEligibilitySnapshot,
    *,
    profile: RudolfWorkProfile = RUDOLF_WORK_PROFILE,
) -> RudolfWorkEligibilityDecision:
    mood_band = get_mood_band(float(snapshot.mood_score))
    if str(snapshot.character_name or "") != profile.character_name:
        return RudolfWorkEligibilityDecision(
            False,
            "unsupported_character",
            mood_band,
        )
    if str(snapshot.world_mode or "") != "sandbox":
        return RudolfWorkEligibilityDecision(
            False,
            "preview_requires_sandbox",
            mood_band,
        )
    if mood_band == "severe":
        return RudolfWorkEligibilityDecision(
            False,
            "severe_mood",
            mood_band,
        )
    return RudolfWorkEligibilityDecision(True, mood_band=mood_band)


def evaluate_rudolf_work_capability(
    asset_manager,
    *,
    mood_score: float,
    resolver: ManifestAnimationResolver | None = None,
    profile: RudolfWorkProfile = RUDOLF_WORK_PROFILE,
) -> RudolfWorkCapabilityDecision:
    resolver = resolver or ManifestAnimationResolver()
    for phase in profile.activity_spec.phases:
        binding = profile.animation_for_phase(phase.name)
        if binding is None:
            return RudolfWorkCapabilityDecision(
                False,
                "missing_phase_binding",
                phase.name,
            )
        resolution = resolver.resolve(
            asset_manager,
            binding.build_request(mood_score),
        )
        if not resolution.found:
            return RudolfWorkCapabilityDecision(
                False,
                resolution.reason or "animation_unavailable",
                phase.name,
            )
    return RudolfWorkCapabilityDecision(True)


def build_rudolf_work_result() -> dict[str, object]:
    return {
        "settlement_key": RUDOLF_WORK_SETTLEMENT_KEY,
        "outcome": "completed",
        "completion_ratio": 1.0,
        "living_fund_delta": RUDOLF_WORK_INCOME,
        "household_pressure_delta": RUDOLF_WORK_PRESSURE_RELIEF,
        "mood_delta": RUDOLF_WORK_MOOD_DELTA,
    }
