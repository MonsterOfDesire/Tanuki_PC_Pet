from __future__ import annotations

from dataclasses import dataclass
import math


SHARED_FOOD_AVAILABLE_SCENE_KINDS = frozenset(("none", "hover_preview"))


@dataclass(frozen=True)
class SharedFoodParticipantState:
    visible: bool = True
    busy: bool = False
    dragging: bool = False
    recovering: bool = False
    social_mode: str = "none"
    perched: bool = False
    offer_scene_kind: str = "none"
    has_held_item: bool = False


@dataclass(frozen=True)
class SharedFoodPartnerEligibility:
    eligible: bool
    reason: str
    distance: float


def evaluate_shared_food_partner_eligibility(
    *,
    holder: SharedFoodParticipantState,
    partner: SharedFoodParticipantState,
    distance: float,
    join_distance: float,
) -> SharedFoodPartnerEligibility:
    try:
        normalized_distance = float(distance)
        normalized_join_distance = max(0.0, float(join_distance))
    except (TypeError, ValueError):
        return SharedFoodPartnerEligibility(False, "invalid_distance", math.inf)
    if not math.isfinite(normalized_distance):
        return SharedFoodPartnerEligibility(False, "invalid_distance", normalized_distance)
    normalized_distance = max(0.0, normalized_distance)

    checks = (
        (not holder.visible, "holder_hidden"),
        (not partner.visible, "partner_hidden"),
        (normalized_distance > normalized_join_distance, "partner_too_far"),
        (holder.busy, "holder_busy"),
        (partner.busy, "partner_busy"),
        (holder.dragging, "holder_dragging"),
        (partner.dragging, "partner_dragging"),
        (holder.recovering, "holder_recovering"),
        (partner.recovering, "partner_recovering"),
        (holder.social_mode != "none", "holder_social_busy"),
        (partner.social_mode != "none", "partner_social_busy"),
        (holder.perched, "holder_perched"),
        (partner.perched, "partner_perched"),
        (
            holder.offer_scene_kind not in SHARED_FOOD_AVAILABLE_SCENE_KINDS,
            "holder_offer_busy",
        ),
        (
            partner.offer_scene_kind not in SHARED_FOOD_AVAILABLE_SCENE_KINDS,
            "partner_offer_busy",
        ),
        (partner.has_held_item, "partner_holding_item"),
    )
    for blocked, reason in checks:
        if blocked:
            return SharedFoodPartnerEligibility(False, reason, normalized_distance)
    return SharedFoodPartnerEligibility(True, "eligible", normalized_distance)


def calculate_shared_food_approach_timeout(
    *,
    distance: float,
    approach_distance: float,
    speed_per_tick: float,
    tick_seconds: float,
    wait_buffer_seconds: float,
    maximum_seconds: float,
) -> float:
    distance_to_cover = max(0.0, float(distance) - max(0.0, float(approach_distance)))
    normalized_speed = max(0.1, float(speed_per_tick))
    estimated_travel_seconds = distance_to_cover / normalized_speed * max(0.001, float(tick_seconds))
    timeout = estimated_travel_seconds + max(0.0, float(wait_buffer_seconds))
    return min(max(0.05, float(maximum_seconds)), max(0.05, timeout))
