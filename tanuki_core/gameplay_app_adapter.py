from __future__ import annotations

from .activity_rhythm_provider import ActivityRhythmProvider


def _build_forwarder(target_getter, target_method):
    def forward(self, *args, **kwargs):
        return getattr(target_getter(self), target_method)(*args, **kwargs)

    forward.__name__ = str(target_method)
    return forward


class GameplayAppAdapterMixin:
    """Compatibility surface for Activity, transformation and reward UI calls."""

    def get_activity_rhythm_snapshot(self, *, now=None):
        provider = getattr(self, "activity_rhythm_provider", None)
        if provider is None:
            provider = ActivityRhythmProvider(
                activity_coordinator=self.activity_coordinator,
                race_executor=self.race_executor,
                chorus_executor=self.chorus_executor,
                sleep_executor=self.sleep_executor,
                pets=self.pets_list,
            )
        return provider.snapshot(now=now)

    def handle_care_activity_event(
        self,
        stage,
        caregiver,
        target,
        *,
        now,
        success=None,
        care_mode="",
    ):
        return self.achievement_runtime_coordinator.handle_care_event(
            stage,
            caregiver,
            target,
            now=now,
            success=success,
            care_mode=care_mode,
        )

    def apply_race_mood_reward(self, target_name, amount):
        return self.gameplay_reward_adapter.apply_mood_reward(
            target_name,
            amount,
        )

    def apply_reverse_race_relationship_reward(
        self,
        actor_name,
        target_name,
        relation_delta,
        occurred_at,
    ):
        return self.gameplay_reward_adapter.apply_relationship_reward(
            actor_name,
            target_name,
            relation_delta,
            occurred_at,
        )

    def apply_chorus_mood_reward(self, target_name, amount):
        return self.gameplay_reward_adapter.apply_mood_reward(
            target_name,
            amount,
        )

    def apply_chorus_relationship_reward(
        self,
        actor_name,
        target_name,
        relation_delta,
        occurred_at,
    ):
        return self.gameplay_reward_adapter.apply_relationship_reward(
            actor_name,
            target_name,
            relation_delta,
            occurred_at,
        )


_ACTIVITY_FORWARDERS = {
    "update_rudolf_work": "update_work",
    "preview_rudolf_work": "preview_work",
    "is_rudolf_work_preview_active": "is_work_preview_active",
    "update_race": "update_race",
    "update_chorus": "update_chorus",
    "preview_chorus": "preview_chorus",
    "is_chorus_preview_active": "is_chorus_preview_active",
    "record_chorus_event": "record_chorus_event",
    "preview_rudolf_teio_race": "preview_race",
    "is_race_preview_active": "is_race_preview_active",
    "record_race_event": "record_race_event",
    "update_sleep": "update_sleep",
    "toggle_sleep_control": "toggle_sleep_control",
    "get_sleep_control_state": "get_sleep_control_state",
    "update_sleep_join_behavior": "update_sleep_join_behavior",
    "interrupt_pet_activity_for_user": "interrupt_pet_for_user",
}

_TRANSFORMATION_FORWARDERS = {
    "toggle_transformation_preview": "toggle_preview",
    "get_transformation_preview_state": "get_preview_state",
    "update_transformations": "update",
    "record_transformation_event": "record_event",
}

for _public_name, _target_name in _ACTIVITY_FORWARDERS.items():
    setattr(
        GameplayAppAdapterMixin,
        _public_name,
        _build_forwarder(
            lambda app: app.activity_runtime_controller,
            _target_name,
        ),
    )

for _public_name, _target_name in _TRANSFORMATION_FORWARDERS.items():
    setattr(
        GameplayAppAdapterMixin,
        _public_name,
        _build_forwarder(
            lambda app: app.transformation_runtime_controller,
            _target_name,
        ),
    )
