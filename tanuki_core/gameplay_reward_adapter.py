from __future__ import annotations

from .transformation_profiles import apply_pet_form_mood_floor


class GameplayRewardAdapter:
    """Applies race/chorus mood and relationship rewards to owned state."""

    def __init__(self, *, pet_registry, household):
        self.pet_registry = pet_registry
        self.household = household

    def apply_mood_reward(self, target_name, amount):
        pet = self.pet_registry.find_by_name(
            target_name,
            visible_only=False,
        )
        if pet is None:
            return False
        pet.mood_score = apply_pet_form_mood_floor(
            pet,
            min(100.0, float(pet.mood_score) + float(amount)),
        )
        sync_mood = getattr(pet, "sync_mood_state_with_score", None)
        if callable(sync_mood):
            sync_mood()
        return True

    def apply_relationship_reward(
        self,
        actor_name,
        target_name,
        relation_delta,
        occurred_at,
    ):
        return self.household.relationships.apply_delta(
            actor_name=str(actor_name or ""),
            target_name=str(target_name or ""),
            relation_delta=dict(relation_delta or {}),
            updated_at=float(occurred_at),
        )
