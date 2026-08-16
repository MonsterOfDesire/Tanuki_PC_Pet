from __future__ import annotations

from .offer_animation_support import OfferAnimationSupport
from .offer_event_adapter import OfferEventAdapter
from .offer_item_scene_runtime_controller import OfferItemSceneSupport
from .pet_registry import PetRegistry


def _compat_app_now():
    # Import lazily so legacy tests patching app_runtime.app_now keep working.
    from . import app_runtime

    return app_runtime.app_now()


class _ControllerStateProperty:
    def __init__(self, attribute, fallback, normalize=None):
        self.attribute = attribute
        self.fallback = fallback
        self.normalize = normalize or (lambda value: value)

    def __get__(self, instance, owner):
        if instance is None:
            return self
        controller = getattr(
            instance,
            "offer_item_scene_runtime_controller",
            None,
        )
        if controller is None:
            return instance.__dict__.get(
                f"_compat_{self.attribute}",
                self.fallback() if callable(self.fallback) else self.fallback,
            )
        return getattr(controller, self.attribute)

    def __set__(self, instance, value):
        value = self.normalize(value)
        controller = getattr(
            instance,
            "offer_item_scene_runtime_controller",
            None,
        )
        if controller is None:
            instance.__dict__[f"_compat_{self.attribute}"] = value
            return
        setattr(controller, self.attribute, value)


class OfferItemSceneAppAdapterMixin:
    """Compatibility façade and support-port builder for app runtime."""

    offer_scene = _ControllerStateProperty("offer_scene", None)
    offer_hover_item_kind = _ControllerStateProperty(
        "offer_hover_item_kind",
        "",
        lambda value: str(value or ""),
    )
    offer_hover_target_name = _ControllerStateProperty(
        "offer_hover_target_name",
        "",
        lambda value: str(value or ""),
    )
    offer_hover_global_x = _ControllerStateProperty(
        "offer_hover_global_x",
        0.0,
        lambda value: float(value or 0.0),
    )
    offer_hover_global_y = _ControllerStateProperty(
        "offer_hover_global_y",
        0.0,
        lambda value: float(value or 0.0),
    )
    offer_hover_started_at = _ControllerStateProperty(
        "offer_hover_started_at",
        0.0,
        lambda value: float(value or 0.0),
    )
    ground_offer_items = _ControllerStateProperty(
        "ground_offer_items",
        list,
    )

    def _get_offer_pet_registry(self):
        registry = getattr(self, "pet_registry", None)
        if registry is None:
            registry = PetRegistry(
                getattr(self, "pets_dict", {}),
                getattr(self, "pets_list", []),
            )
            self.pet_registry = registry
        return registry

    def _get_offer_animation_support(self):
        support = getattr(self, "offer_animation_support", None)
        if support is None:
            support = OfferAnimationSupport(
                pets=getattr(self, "pets_list", []),
                pet_registry=self._get_offer_pet_registry(),
                lock_pet_for_offer_scene=(
                    lambda pet, scene_kind, until: self.lock_pet_for_offer_scene(
                        pet,
                        scene_kind,
                        until,
                    )
                ),
                held_item_position_updater=(
                    lambda *args, **kwargs: (
                        self.update_held_offer_widget_position(
                            *args,
                            **kwargs,
                        )
                    )
                ),
                now_provider=_compat_app_now,
            )
            self.offer_animation_support = support
        return support

    def _get_offer_event_adapter(self):
        adapter = getattr(self, "offer_event_adapter", None)
        if adapter is None:
            adapter = OfferEventAdapter(
                achievement_runtime_coordinator=(
                    self.achievement_runtime_coordinator
                ),
                pet_registry=self._get_offer_pet_registry(),
                record_household_event=(
                    lambda **kwargs: self.record_household_event(**kwargs)
                ),
                scene_provider=lambda: self.offer_scene,
                scene_id_provider=(
                    lambda scene: self.item_scene_coordinator.get_scene_id(
                        scene
                    )
                ),
                now_provider=_compat_app_now,
            )
            self.offer_event_adapter = adapter
        return adapter

    def _build_offer_item_scene_support(self):
        controller = lambda: self.offer_item_scene_runtime_controller
        dynamic = lambda method_name: (
            lambda *args, **kwargs: getattr(self, method_name)(
                *args,
                **kwargs,
            )
        )
        direct = lambda method_name: (
            lambda *args, **kwargs: getattr(
                self.direct_hover_scene_executor,
                method_name,
            )(
                controller(),
                *args,
                **kwargs,
            )
        )
        shared = lambda method_name: (
            lambda *args, **kwargs: getattr(
                self.shared_food_scene_executor,
                method_name,
            )(
                controller(),
                *args,
                **kwargs,
            )
        )
        return OfferItemSceneSupport(
            apply_offer_hover_miss=(
                lambda pet, item_kind: (
                    self.direct_hover_scene_executor.apply_offer_hover_miss(
                        controller(),
                        pet,
                        item_kind,
                        now=controller().now_provider(),
                    )
                )
            ),
            pet_is_busy_for_offer_interaction=dynamic(
                "pet_is_busy_for_offer_interaction"
            ),
            pet_can_interact_with_offer_item=dynamic(
                "pet_can_interact_with_offer_item"
            ),
            find_offer_drop_target=dynamic("find_offer_drop_target"),
            find_offer_hover_target=dynamic("find_offer_hover_target"),
            apply_offer_negative_afterglow=direct(
                "apply_offer_negative_afterglow"
            ),
            apply_offer_hover_timeout_stage=direct(
                "apply_offer_hover_timeout_stage"
            ),
            apply_offer_hover_cursor_avoidance=direct(
                "apply_offer_hover_cursor_avoidance"
            ),
            apply_scene_context_with_preferences=dynamic(
                "apply_scene_context_with_preferences"
            ),
            apply_scene_contexts_with_preferences=dynamic(
                "apply_scene_contexts_with_preferences"
            ),
            apply_scene_candidates_with_preferences=dynamic(
                "apply_scene_candidates_with_preferences"
            ),
            apply_scene_reaction_with_preferences=dynamic(
                "apply_scene_reaction_with_preferences"
            ),
            order_candidates_by_purpose=dynamic(
                "order_candidates_by_purpose"
            ),
            update_direct_offer_accept_motion=dynamic(
                "update_direct_offer_accept_motion"
            ),
            choose_honey_guardian_for_child=dynamic(
                "choose_honey_guardian_for_child"
            ),
            choose_bottle_feed_child_for_holder=dynamic(
                "choose_bottle_feed_child_for_holder"
            ),
            interrupt_pet_window_motion_for_offer=dynamic(
                "interrupt_pet_window_motion_for_offer"
            ),
            pet_is_window_transitioning_for_offer=dynamic(
                "pet_is_window_transitioning_for_offer"
            ),
            prepare_pet_window_state_for_offer=dynamic(
                "prepare_pet_window_state_for_offer"
            ),
            reset_offer_scene_pet_motion=dynamic(
                "reset_offer_scene_pet_motion"
            ),
            update_held_offer_widget_position=dynamic(
                "update_held_offer_widget_position"
            ),
            apply_held_item_behavior=dynamic("apply_held_item_behavior"),
            get_shared_food_capability_contexts=shared(
                "get_shared_food_capability_contexts"
            ),
            get_shared_food_candidate_result=shared(
                "get_shared_food_candidate_result"
            ),
            filter_shared_food_candidates=shared(
                "filter_shared_food_candidates"
            ),
            build_runtime_shared_food_capabilities=shared(
                "build_runtime_shared_food_capabilities"
            ),
            apply_shared_food_capability=shared(
                "apply_shared_food_capability"
            ),
            apply_shared_food_role_action=shared(
                "apply_shared_food_role_action"
            ),
            build_shared_food_achievement_metadata=dynamic(
                "build_shared_food_achievement_metadata"
            ),
            apply_offer_mood_reward=dynamic("apply_offer_mood_reward"),
            record_offer_event=dynamic("record_offer_event"),
            record_household_event=dynamic("record_household_event"),
            start_direct_offer_scene=dynamic("start_direct_offer_scene"),
            start_bottle_feed_scene=dynamic("start_bottle_feed_scene"),
            start_shared_food_scene=dynamic("start_shared_food_scene"),
            start_honey_guard_scene=dynamic("start_honey_guard_scene"),
            build_offer_item_widget=dynamic("build_offer_item_widget"),
            drop_ground_offer_item=dynamic("drop_ground_offer_item"),
            ensure_pet_held_item=dynamic("ensure_pet_held_item"),
            record_shared_food_event=dynamic("record_shared_food_event"),
            update_shared_food_scene=dynamic("update_shared_food_scene"),
        )


def _build_forwarder(target_getter, target_method):
    def forward(self, *args, **kwargs):
        target = target_getter(self)
        return getattr(target, target_method)(*args, **kwargs)

    forward.__name__ = str(target_method).lstrip("_")
    return forward


_CONTROLLER_FORWARDERS = {
    "lock_pet_for_offer_scene": "lock_pet_for_offer_scene",
    "unlock_pet_offer_scene": "unlock_pet_offer_scene",
    "refresh_offer_scene_locks": "refresh_offer_scene_locks",
    "clear_offer_scene": "clear_offer_scene",
    "clear_offer_hover": "clear_offer_hover",
    "apply_offer_hover_miss": "apply_offer_hover_miss",
    "cancel_offer_scene_if_hidden_participants": (
        "cancel_offer_scene_if_hidden_participants"
    ),
    "hover_timeout_scene_accepts_offer_drop": (
        "hover_timeout_scene_accepts_offer_drop"
    ),
    "finalize_offer_hover_timeout_failure": (
        "finalize_offer_hover_timeout_failure"
    ),
    "start_offer_interaction_for_target": (
        "start_offer_interaction_for_target"
    ),
    "clear_ground_offer_items": "clear_ground_offer_items",
    "clear_pet_held_item": "clear_pet_held_item",
    "build_offer_item_widget": "_build_offer_item_widget",
    "ensure_pet_held_item": "_ensure_pet_held_item",
    "find_ground_offer_item_by_widget": (
        "find_ground_offer_item_by_widget"
    ),
    "handle_offer_hover": "handle_offer_hover",
    "handle_offer_drop": "handle_offer_drop",
    "handle_ground_offer_item_drop": "handle_ground_offer_item_drop",
    "apply_offer_negative_afterglow": "apply_offer_negative_afterglow",
    "apply_offer_hover_timeout_stage": "apply_offer_hover_timeout_stage",
    "apply_offer_hover_cursor_avoidance": (
        "apply_offer_hover_cursor_avoidance"
    ),
    "start_offer_hover_timeout_scene": "start_offer_hover_timeout_scene",
    "get_shared_food_capability_contexts": (
        "get_shared_food_capability_contexts"
    ),
    "get_shared_food_candidate_result": "get_shared_food_candidate_result",
    "filter_shared_food_candidates": "filter_shared_food_candidates",
    "build_runtime_shared_food_capabilities": (
        "build_runtime_shared_food_capabilities"
    ),
    "apply_shared_food_capability": "apply_shared_food_capability",
    "apply_shared_food_role_action": "apply_shared_food_role_action",
    "capture_shared_food_animation": "capture_shared_food_animation",
    "apply_shared_food_scene_lock_state": (
        "apply_shared_food_scene_lock_state"
    ),
    "update_pet_held_items": "update_pet_held_items",
    "start_direct_offer_scene": "_start_direct_offer_scene",
    "start_bottle_feed_scene": "_start_bottle_feed_scene",
    "build_shared_food_participant_state": (
        "build_shared_food_participant_state"
    ),
    "pet_is_unavailable_during_shared_food": (
        "pet_is_unavailable_during_shared_food"
    ),
    "evaluate_runtime_shared_food_partner": (
        "evaluate_runtime_shared_food_partner"
    ),
    "get_shared_food_approach_timeout": "get_shared_food_approach_timeout",
    "find_shared_food_partner": "find_shared_food_partner",
    "start_shared_food_scene": "_start_shared_food_scene",
    "start_honey_guard_scene": "_start_honey_guard_scene",
    "_begin_offer_achievement_session": "_begin_offer_achievement_session",
    "apply_shared_food_outcome_effects": (
        "apply_shared_food_outcome_effects"
    ),
    "drop_ground_offer_item": "_drop_ground_offer_item",
    "place_ground_offer_item": "place_ground_offer_item",
    "remove_ground_offer_item": "remove_ground_offer_item",
    "update_ground_offer_items": "update_ground_offer_items",
    "try_pickup_ground_offer_item": "try_pickup_ground_offer_item",
    "update_offer_scene": "update_offer_scene",
    "update_offer_hover_preview": "update_offer_hover_preview",
    "update_offer_hover_timeout_reaction_scene": (
        "update_offer_hover_timeout_reaction_scene"
    ),
    "update_direct_offer_scene": "update_direct_offer_scene",
    "update_deny_only_offer_scene": "update_deny_only_offer_scene",
    "update_bottle_feed_scene": "update_bottle_feed_scene",
    "set_shared_food_stage": "set_shared_food_stage",
    "hide_shared_food_item": "hide_shared_food_item",
    "fallback_shared_food_to_solo": "fallback_shared_food_to_solo",
    "resolve_active_shared_food_outcome": "resolve_active_shared_food_outcome",
    "get_shared_food_consume_stage_seconds": (
        "get_shared_food_consume_stage_seconds"
    ),
    "apply_shared_food_stage_animations": (
        "apply_shared_food_stage_animations"
    ),
    "update_shared_food_scene": "_update_shared_food_scene",
    "update_honey_guard_scene": "update_honey_guard_scene",
}

_ANIMATION_FORWARDERS = {
    "pet_is_busy_for_offer_interaction": (
        "pet_is_busy_for_offer_interaction"
    ),
    "pet_can_interact_with_offer_item": "pet_can_interact_with_offer_item",
    "find_offer_drop_target": "find_offer_drop_target",
    "find_offer_hover_target": "find_offer_hover_target",
    "get_offer_reference_frame": "get_offer_reference_frame",
    "get_offer_reference_frame_for_context": (
        "get_offer_reference_frame_for_context"
    ),
    "get_offer_hotspot_global_position": "get_offer_hotspot_global_position",
    "update_held_offer_widget_position": (
        "update_held_offer_widget_position"
    ),
    "choose_honey_guardian_for_child": "choose_honey_guardian_for_child",
    "choose_bottle_feed_child_for_holder": (
        "choose_bottle_feed_child_for_holder"
    ),
    "interrupt_pet_window_motion_for_offer": (
        "interrupt_pet_window_motion_for_offer"
    ),
    "pet_is_window_transitioning_for_offer": (
        "pet_is_window_transitioning_for_offer"
    ),
    "prepare_pet_window_state_for_offer": "prepare_pet_window_state_for_offer",
    "reset_offer_scene_pet_motion": "reset_offer_scene_pet_motion",
    "scene_animation_matches_preferences": (
        "scene_animation_matches_preferences"
    ),
    "apply_scene_context_with_preferences": (
        "apply_scene_context_with_preferences"
    ),
    "apply_scene_contexts_with_preferences": (
        "apply_scene_contexts_with_preferences"
    ),
    "order_candidates_by_purpose": "order_candidates_by_purpose",
    "current_direct_offer_accept_is_mobile": (
        "current_direct_offer_accept_is_mobile"
    ),
    "update_direct_offer_accept_motion": "update_direct_offer_accept_motion",
    "apply_scene_candidates_with_preferences": (
        "apply_scene_candidates_with_preferences"
    ),
    "apply_scene_reaction_with_preferences": (
        "apply_scene_reaction_with_preferences"
    ),
    "apply_held_item_behavior": "apply_held_item_behavior",
}

_EVENT_FORWARDERS = {
    "record_offer_event": "record_offer_event",
    "record_shared_food_event": "record_shared_food_event",
    "build_shared_food_achievement_metadata": (
        "build_shared_food_achievement_metadata"
    ),
    "apply_offer_mood_reward": "apply_offer_mood_reward",
}

for _public_name, _target_name in _CONTROLLER_FORWARDERS.items():
    setattr(
        OfferItemSceneAppAdapterMixin,
        _public_name,
        _build_forwarder(
            lambda app: app.offer_item_scene_runtime_controller,
            _target_name,
        ),
    )

for _public_name, _target_name in _ANIMATION_FORWARDERS.items():
    setattr(
        OfferItemSceneAppAdapterMixin,
        _public_name,
        _build_forwarder(
            lambda app: app._get_offer_animation_support(),
            _target_name,
        ),
    )

for _public_name, _target_name in _EVENT_FORWARDERS.items():
    setattr(
        OfferItemSceneAppAdapterMixin,
        _public_name,
        _build_forwarder(
            lambda app: app._get_offer_event_adapter(),
            _target_name,
        ),
    )
