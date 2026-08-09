from __future__ import annotations

from dataclasses import dataclass

from .chorus_state import ChorusEvent


CHORUS_PERFORMER_MOOD_REWARD = 2.0
CHORUS_AUDIENCE_MOOD_REWARD = 1.0
CHORUS_PERFORMER_FAMILIARITY_REWARD = 2.0
CHORUS_PERFORMER_TRUST_REWARD = 1.0
CHORUS_AUDIENCE_FAMILIARITY_REWARD = 1.0


@dataclass(frozen=True)
class ChorusMoodReward:
    character_name: str
    amount: float


@dataclass(frozen=True)
class ChorusRelationshipReward:
    actor_name: str
    target_name: str
    familiarity: float = 0.0
    trust: float = 0.0

    @property
    def relation_delta(self) -> dict[str, float]:
        return {
            "familiarity": float(self.familiarity),
            "trust": float(self.trust),
        }


@dataclass(frozen=True)
class ChorusSettlementPlan:
    mood_rewards: tuple[ChorusMoodReward, ...] = ()
    relationship_rewards: tuple[ChorusRelationshipReward, ...] = ()

    @property
    def empty(self) -> bool:
        return not self.mood_rewards and not self.relationship_rewards


def build_chorus_settlement_plan(event: ChorusEvent) -> ChorusSettlementPlan:
    if (
        event.event_type != "chorus_completed"
        or event.source == "settings_preview"
    ):
        return ChorusSettlementPlan()

    performers = tuple(dict.fromkeys(event.performer_names))
    audiences = tuple(dict.fromkeys(event.audience_names))
    mood_rewards = tuple(
        ChorusMoodReward(name, CHORUS_PERFORMER_MOOD_REWARD)
        for name in performers
    ) + tuple(
        ChorusMoodReward(name, CHORUS_AUDIENCE_MOOD_REWARD)
        for name in audiences
    )

    relationship_rewards = []
    for actor_name in performers:
        for target_name in performers:
            if actor_name == target_name:
                continue
            relationship_rewards.append(
                ChorusRelationshipReward(
                    actor_name=actor_name,
                    target_name=target_name,
                    familiarity=CHORUS_PERFORMER_FAMILIARITY_REWARD,
                    trust=CHORUS_PERFORMER_TRUST_REWARD,
                )
            )
    for audience_name in audiences:
        for performer_name in performers:
            if audience_name == performer_name:
                continue
            relationship_rewards.append(
                ChorusRelationshipReward(
                    actor_name=audience_name,
                    target_name=performer_name,
                    familiarity=CHORUS_AUDIENCE_FAMILIARITY_REWARD,
                )
            )

    return ChorusSettlementPlan(
        mood_rewards=mood_rewards,
        relationship_rewards=tuple(relationship_rewards),
    )
