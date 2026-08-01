from __future__ import annotations

from dataclasses import dataclass

from .transformation_state import FORM_BASE, FORM_TRANSFORMED


TRANSFORMED_RUDOLF_NAME = "Symboli Rudolf"
TRANSFORMED_RUDOLF_SOCIAL_OBSERVERS = frozenset(
    {
        "Air Groove",
        "Tokai Teio",
        "Tsurumaru Tsuyoshi",
    }
)
TRANSFORMED_RUDOLF_FOCUS_DISTANCE = 320.0
TRANSFORMED_RUDOLF_OBSERVE_CHANCE_BONUS = 0.15
TRANSFORMED_RUDOLF_POST_OBSERVE_CHANCE_BONUS = 0.15
TRANSFORMED_RUDOLF_SOCIAL_DISTANCE_MULTIPLIER = 1.35
TRANSFORMED_RUDOLF_SOCIAL_COOLDOWN_MULTIPLIER = 0.65
TRANSFORMED_RUDOLF_RELATION_MULTIPLIER = 1.5
TRANSFORMED_RUDOLF_EXPRESSION_FAMILIARITY_FLOOR = 6.0
POSITIVE_RELATION_KEYS = frozenset(
    {"familiarity", "trust", "attachment"}
)


@dataclass(frozen=True)
class TransformedRudolfInfluence:
    active: bool = False
    target_name: str = ""
    target_distance: float = 0.0
    observe_chance_bonus: float = 0.0
    post_observe_chance_bonus: float = 0.0
    expression_familiarity_floor: float = 0.0


def is_transformed_rudolf_social_pair(
    *,
    observer_name: str,
    observer_form: str,
    target_name: str,
    target_form: str,
) -> bool:
    return bool(
        str(observer_name or "")
        in TRANSFORMED_RUDOLF_SOCIAL_OBSERVERS
        and str(observer_form or FORM_BASE) == FORM_BASE
        and str(target_name or "") == TRANSFORMED_RUDOLF_NAME
        and str(target_form or FORM_BASE) == FORM_TRANSFORMED
    )


def resolve_transformed_rudolf_influence(
    *,
    observer_name: str,
    observer_form: str,
    target_name: str,
    target_form: str,
    target_visible: bool,
    target_distance: float,
    blocked_target_name: str = "",
) -> TransformedRudolfInfluence:
    if not is_transformed_rudolf_social_pair(
        observer_name=observer_name,
        observer_form=observer_form,
        target_name=target_name,
        target_form=target_form,
    ):
        return TransformedRudolfInfluence()
    distance = float(target_distance or 0.0)
    if (
        not target_visible
        or distance <= 0.0
        or distance > TRANSFORMED_RUDOLF_FOCUS_DISTANCE
        or str(blocked_target_name or "") == TRANSFORMED_RUDOLF_NAME
    ):
        return TransformedRudolfInfluence()
    return TransformedRudolfInfluence(
        active=True,
        target_name=TRANSFORMED_RUDOLF_NAME,
        target_distance=distance,
        observe_chance_bonus=(
            TRANSFORMED_RUDOLF_OBSERVE_CHANCE_BONUS
        ),
        post_observe_chance_bonus=(
            TRANSFORMED_RUDOLF_POST_OBSERVE_CHANCE_BONUS
        ),
        expression_familiarity_floor=(
            TRANSFORMED_RUDOLF_EXPRESSION_FAMILIARITY_FLOOR
        ),
    )


def get_transformed_rudolf_social_distance(
    base_distance: float,
    *,
    influenced: bool,
) -> float:
    multiplier = (
        TRANSFORMED_RUDOLF_SOCIAL_DISTANCE_MULTIPLIER
        if influenced
        else 1.0
    )
    return round(float(base_distance) * multiplier, 3)


def get_transformed_rudolf_social_cooldown(
    base_seconds: float,
    *,
    influenced: bool,
) -> float:
    multiplier = (
        TRANSFORMED_RUDOLF_SOCIAL_COOLDOWN_MULTIPLIER
        if influenced
        else 1.0
    )
    return round(float(base_seconds) * multiplier, 3)


def amplify_transformed_rudolf_positive_relation_delta(
    relation_delta: dict[str, float],
    *,
    influenced: bool,
) -> dict[str, float]:
    resolved = {
        str(key): float(value)
        for key, value in dict(relation_delta or {}).items()
    }
    if not influenced or any(value < 0.0 for value in resolved.values()):
        return resolved
    for key in POSITIVE_RELATION_KEYS:
        if resolved.get(key, 0.0) > 0.0:
            resolved[key] = round(
                resolved[key]
                * TRANSFORMED_RUDOLF_RELATION_MULTIPLIER,
                3,
            )
    return resolved
