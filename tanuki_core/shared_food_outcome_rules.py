from __future__ import annotations

from dataclasses import dataclass
import math

from .shared_food_profiles import (
    SHARED_FOOD_OUTCOME_DEFINITIONS_BY_KEY,
    SHARED_FOOD_OUTCOME_HOLDER_GIVES,
    SHARED_FOOD_OUTCOME_HOLDER_KEEPS,
    SHARED_FOOD_OUTCOME_KEYS,
    SHARED_FOOD_OUTCOME_SHARE_BOTH,
    SHARED_FOOD_ROLE_HOLDER,
    SHARED_FOOD_ROLE_PARTNER,
    SharedFoodCharacterCapabilities,
    SharedFoodProfile,
)


NormalizedOutcomeWeights = tuple[tuple[str, float], ...]


@dataclass(frozen=True)
class SharedFoodOutcomeResolution:
    outcome_key: str = ""
    available_outcomes: tuple[str, ...] = ()
    normalized_weights: NormalizedOutcomeWeights = ()
    consume_order: tuple[str, ...] = ()
    roll: float = 0.0
    reason: str = ""

    @property
    def resolved(self) -> bool:
        return bool(self.outcome_key)

    def weight_for(self, outcome_key: str) -> float:
        for key, weight in self.normalized_weights:
            if key == outcome_key:
                return weight
        return 0.0


def is_valid_shared_food_pair(
    profile: SharedFoodProfile | None,
    holder_name: str,
    partner_name: str,
) -> bool:
    if profile is None or holder_name not in profile.allowed_holders:
        return False
    return partner_name in profile.partner_names_for_holder(holder_name)


def _has_capability(
    capabilities: SharedFoodCharacterCapabilities,
    capability_name: str,
) -> bool:
    return bool(getattr(capabilities, f"{capability_name}_candidates", ()))


def preflight_shared_food_outcomes(
    profile: SharedFoodProfile | None,
    holder_name: str,
    partner_name: str,
    *,
    holder_capabilities: SharedFoodCharacterCapabilities | None = None,
    partner_capabilities: SharedFoodCharacterCapabilities | None = None,
) -> tuple[str, ...]:
    if not is_valid_shared_food_pair(profile, holder_name, partner_name):
        return ()
    holder_capabilities = holder_capabilities or profile.capabilities_for(holder_name)
    partner_capabilities = partner_capabilities or profile.capabilities_for(partner_name)
    if holder_capabilities is None or partner_capabilities is None:
        return ()
    if not _has_capability(holder_capabilities, "hold"):
        return ()
    if not _has_capability(partner_capabilities, "approach"):
        return ()
    if not _has_capability(holder_capabilities, "watch"):
        return ()
    if not _has_capability(partner_capabilities, "request"):
        return ()

    available: list[str] = []
    if (
        _has_capability(holder_capabilities, "consume")
        and _has_capability(partner_capabilities, "consume")
        and _has_capability(holder_capabilities, "react")
        and _has_capability(partner_capabilities, "react")
    ):
        available.append(SHARED_FOOD_OUTCOME_SHARE_BOTH)
    if (
        _has_capability(holder_capabilities, "consume")
        and _has_capability(partner_capabilities, "react")
    ):
        available.append(SHARED_FOOD_OUTCOME_HOLDER_KEEPS)
    if (
        _has_capability(partner_capabilities, "consume")
        and _has_capability(holder_capabilities, "react")
    ):
        available.append(SHARED_FOOD_OUTCOME_HOLDER_GIVES)
    return tuple(available)


def _normalize_roll(roll: float) -> float:
    try:
        normalized = float(roll)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(normalized):
        return 0.0
    return min(1.0, max(0.0, normalized))


def resolve_shared_food_outcome(
    profile: SharedFoodProfile | None,
    holder_name: str,
    partner_name: str,
    *,
    roll: float,
    available_outcomes: tuple[str, ...] | None = None,
    holder_capabilities: SharedFoodCharacterCapabilities | None = None,
    partner_capabilities: SharedFoodCharacterCapabilities | None = None,
    weight_multipliers_by_key: dict[str, float] | None = None,
) -> SharedFoodOutcomeResolution:
    normalized_roll = _normalize_roll(roll)
    if not is_valid_shared_food_pair(profile, holder_name, partner_name):
        return SharedFoodOutcomeResolution(
            roll=normalized_roll,
            reason="invalid_pair",
        )

    preflight_outcomes = preflight_shared_food_outcomes(
        profile,
        holder_name,
        partner_name,
        holder_capabilities=holder_capabilities,
        partner_capabilities=partner_capabilities,
    )
    if available_outcomes is None:
        eligible_outcomes = preflight_outcomes
    else:
        requested_outcomes = set(available_outcomes)
        eligible_outcomes = tuple(
            outcome_key
            for outcome_key in preflight_outcomes
            if outcome_key in requested_outcomes
        )
    if not eligible_outcomes:
        return SharedFoodOutcomeResolution(
            available_outcomes=(),
            roll=normalized_roll,
            reason="no_available_outcomes",
        )

    multipliers = weight_multipliers_by_key or {}
    weighted_outcomes: list[tuple[str, float]] = []
    for outcome_key in SHARED_FOOD_OUTCOME_KEYS:
        if outcome_key not in eligible_outcomes:
            continue
        base_weight = float(profile.outcome_weights_by_key.get(outcome_key, 0.0) or 0.0)
        multiplier = float(multipliers.get(outcome_key, 1.0) or 0.0)
        adjusted_weight = base_weight * max(0.0, multiplier)
        if adjusted_weight > 0.0:
            weighted_outcomes.append((outcome_key, adjusted_weight))
    total_weight = sum(weight for _, weight in weighted_outcomes)
    if total_weight <= 0.0:
        return SharedFoodOutcomeResolution(
            available_outcomes=eligible_outcomes,
            roll=normalized_roll,
            reason="no_positive_outcome_weights",
        )

    normalized_weights = tuple(
        (outcome_key, weight / total_weight)
        for outcome_key, weight in weighted_outcomes
    )
    threshold = normalized_roll
    cumulative = 0.0
    selected_outcome = normalized_weights[-1][0]
    for outcome_key, normalized_weight in normalized_weights:
        cumulative += normalized_weight
        if threshold < cumulative and not math.isclose(
            threshold,
            cumulative,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            selected_outcome = outcome_key
            break
    definition = SHARED_FOOD_OUTCOME_DEFINITIONS_BY_KEY[selected_outcome]
    return SharedFoodOutcomeResolution(
        outcome_key=selected_outcome,
        available_outcomes=eligible_outcomes,
        normalized_weights=normalized_weights,
        consume_order=definition.consume_order,
        roll=normalized_roll,
    )


def get_shared_food_consumer_names(
    consume_order: tuple[str, ...],
    holder_name: str,
    partner_name: str,
) -> tuple[str, ...]:
    name_by_role = {
        SHARED_FOOD_ROLE_HOLDER: holder_name,
        SHARED_FOOD_ROLE_PARTNER: partner_name,
    }
    return tuple(
        name_by_role[role]
        for role in consume_order
        if role in name_by_role
    )
