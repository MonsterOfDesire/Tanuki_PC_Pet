from __future__ import annotations

from dataclasses import dataclass


AUTONOMOUS_OFFER_SOURCE = "autonomous_offer"
AUTONOMOUS_GROUND_SOURCE = "autonomous_ground"
AUTONOMOUS_OFFER_INITIAL_MIN_SECONDS = 60.0
AUTONOMOUS_OFFER_INITIAL_MAX_SECONDS = 120.0
AUTONOMOUS_OFFER_COOLDOWN_MIN_SECONDS = 180.0
AUTONOMOUS_OFFER_COOLDOWN_MAX_SECONDS = 300.0
AUTONOMOUS_OFFER_RETRY_MIN_SECONDS = 20.0
AUTONOMOUS_OFFER_RETRY_MAX_SECONDS = 40.0
AUTONOMOUS_OFFER_PREVIEW_MIN_SECONDS = 4.0
AUTONOMOUS_OFFER_PREVIEW_MAX_SECONDS = 5.0


@dataclass
class AutonomousOfferScheduleState:
    next_proposal_at: float = 0.0


@dataclass(frozen=True)
class AutonomousOfferPreviewState:
    item_kind: str
    actor_name: str
    started_at: float
    ends_at: float


@dataclass(frozen=True)
class AutonomousOfferOpportunity:
    item_kind: str
    actor_name: str
    delivery_kind: str = "direct"
    weight: float = 1.0


def choose_autonomous_offer_opportunity(opportunities, *, roll: float):
    candidates = tuple(opportunities or ())
    if not candidates:
        return None
    weights = tuple(max(0.0, float(item.weight)) for item in candidates)
    total = sum(weights)
    if total <= 0.0:
        return candidates[0]
    cursor = max(0.0, min(0.999999999, float(roll))) * total
    accumulated = 0.0
    for candidate, weight in zip(candidates, weights):
        accumulated += weight
        if cursor < accumulated:
            return candidate
    return candidates[-1]
